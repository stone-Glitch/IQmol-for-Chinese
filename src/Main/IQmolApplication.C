/*******************************************************************************
       
  Copyright (C) 2022 Andrew Gilbert
           
  This file is part of IQmol, a free molecular visualization program. See
  <http://iqmol.org> for more details.
       
  IQmol is free software: you can redistribute it and/or modify it under the
  terms of the GNU General Public License as published by the Free Software
  Foundation, either version 3 of the License, or (at your option) any later
  version.

  IQmol is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
  FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
  details.
      
  You should have received a copy of the GNU General Public License along
  with IQmol.  If not, see <http://www.gnu.org/licenses/>.  
   
********************************************************************************/

#include "IQmolApplication.h"
#include "MainWindow.h"
#include "ControlServer.h"
#include "ViewerModel.h"
#include "Layer/Layer.h"
#include "Layer/FrequenciesLayer.h"
#include "Layer/GeometryListLayer.h"
#include "Layer/MolecularSurfacesLayer.h"
#include "Layer/SurfaceLayer.h"
#include "Data/SurfaceInfo.h"
#include "Data/SurfaceType.h"
#include "JobMonitor.h"
#include "ServerRegistry.h"
#include "Preferences.h"
#include "QMsgBox.h"
#include "QsLog.h"
#include <QDir>
#include <QString>
#include <QLibrary>
#include <QMessageBox>
#include <QFileOpenEvent>
#include <QFileInfo>
#include <QEventLoop>
#include <QJsonArray>
#include <QJsonObject>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QLocalSocket>
#include <QSplashScreen>
#include <QTimer>
#include <QTranslator>
#include <QLibraryInfo>
#include <QLocale>

#include <QDebug>
#include <QThread>
#include <QThreadPool>

#include <exception>


namespace IQmol {

IQmolApplication::IQmolApplication(int &argc, char **argv )
  : QApplication(argc, argv), m_splashScreen(0), m_qtTranslator(0), m_appTranslator(0),
    m_unhandledException(QMessageBox::Critical, "IQmol", "IQmol encountered an exception.\n"
    "See log file for details.", QMessageBox::Abort),
    m_controlServer(0), m_controlBusy(false)
    
{
   setOrganizationDomain("iqmol.org");
   setApplicationName("IQmol");
   // 加载中文本地化翻译（Qt 基础翻译 + 应用翻译）
   loadTranslations();
   if (argc > 1) {
      QString arg(argv[1]);
      if (arg == "--clear-jobs") {
         qDebug() << "Clearing past jobs from preferences";
         Preferences::JobMonitorList(QVariantList());
      }
  }
   // The control channel must never prevent IQmol from starting, so any
   // failure here is logged and ignored.
   startControlServer();
   // Can't log anything yet as the logger hasn't been initialized
}


void IQmolApplication::startControlServer()
{
   if (qEnvironmentVariableIsSet("IQMOL_NO_CONTROL")) {
      qDebug() << "[control] disabled by IQMOL_NO_CONTROL";
      return;
   }

   m_controlServer = new ControlServer(this);
   connect(m_controlServer, &ControlServer::commandReceived,
      this, &IQmolApplication::onControlCommand);

   QString error;
   if (!m_controlServer->start(&error)) {
      qDebug() << "[control] unavailable:" << error;
      delete m_controlServer;
      m_controlServer = 0;
      return;
   }
   qDebug() << "[control] listening, endpoint:" << m_controlServer->endpointPath();
}


namespace {

   // How long a "load" request waits for the parser to finish before giving
   // up. Parsing happens on a background task, so the reply cannot be sent
   // synchronously.
   const int kLoadTimeoutMs = 20000;

   MainWindow* findMainWindow()
   {
      for (QWidget* widget : QApplication::topLevelWidgets()) {
         MainWindow* mw(qobject_cast<MainWindow*>(widget));
         if (mw) return mw;
      }
      return 0;
   }

   // Nested: layers live several levels below the system root (Molecule ->
   // MolecularSurfaces -> Surface), so Children alone is not enough.
   const unsigned kSceneLayers = Layer::Children | Layer::Nested;

   QJsonArray describeSurfaces(MainWindow* mw)
   {
      QJsonArray out;
      QList<Layer::Surface*> surfaces(
         mw->viewerModel().controlFindLayers<Layer::Surface>(kSceneLayers));
      for (Layer::Surface* s : surfaces) {
         QJsonObject o;
         o["name"]        = s->text();                       // translated
         o["key"]         = s->data(Qt::UserRole).toString(); // stable English key
         o["visible"]     = (s->checkState() == Qt::Checked);
         o["area"]        = s->surfaceArea();
         o["signed"]      = s->surfaceSigned();
         o["hasProperty"] = s->surfaceHasProperty();
         out.append(o);
      }
      return out;
   }

   QMap<QString, Data::SurfaceType::Kind> surfaceKinds()
   {
      QMap<QString, Data::SurfaceType::Kind> kinds;
      kinds["vdw"]         = Data::SurfaceType::VanDerWaals;
      kinds["promolecule"] = Data::SurfaceType::Promolecule;
      kinds["sid"]         = Data::SurfaceType::SID;
      return kinds;
   }

}


void IQmolApplication::onControlCommand(QLocalSocket* client, QJsonObject const& request)
{
   const QString     cmd (request.value("cmd").toString());
   // id 由客户端定义，按要求原样回显。历史实现用 toString()，客户端若传数字
   // 就会回成空串、无法与请求配对，故保留 QJsonValue 的原始类型。
   const QJsonValue  idValue(request.value("id"));
   const QJsonValue  id(idValue.isUndefined() ? QJsonValue(QString()) : idValue);
   const QJsonObject args(request.value("args").toObject());

   auto respond = [&](QJsonObject const& result) {
      QJsonObject res;
      res["v"]      = 1;
      res["id"]     = id;
      res["ok"]     = true;
      res["result"] = result;
      m_controlServer->sendResponse(client, res);
   };

   auto fail = [&](QString const& code, QString const& message) {
      QJsonObject err;
      err["code"]    = code;
      err["message"] = message;

      QJsonObject res;
      res["v"]     = 1;
      res["id"]    = id;
      res["ok"]    = false;
      res["error"] = err;
      m_controlServer->sendResponse(client, res);
   };

   // "load" runs a nested event loop while the parser works. Refuse anything
   // that arrives meanwhile rather than re-entering.
   if (m_controlBusy) {
      fail("BUSY", "another command is being processed");
      return;
   }

   if (cmd == "ping") {
      QJsonObject result;
      result["pong"] = true;
      respond(result);
      return;
   }

   if (cmd == "state") {
      QJsonObject scene;
      MainWindow* mw(findMainWindow());
      if (mw) {
         scene["molecules"] = mw->viewerModel().moleculeList(false).size();
         scene["surfaces"]  = describeSurfaces(mw).size();
         scene["tracks"]    = mw->viewerModel()
            .controlFindLayers<Layer::GeometryList>(kSceneLayers).size();
         scene["animating"] = mw->viewer() ? mw->viewer()->animationIsStarted() : false;
      }else {
         scene["windowReady"] = false;
      }

      QJsonObject result;
      result["pid"]      = (qint64)QCoreApplication::applicationPid();
      result["version"]  = IQMOL_VERSION_STR;
      result["tag"]      = IQMOL_GIT_VERSION;
      result["packageVersion"] = QString(IQMOL_PACKAGE_VERSION);
      result["startedAt"] = m_controlServer->startedAt();
      // QSet iteration order is unspecified; sort so callers can diff/assert.
      QStringList commands(m_controlServer->allowedCommands().toList());
      commands.sort();
      result["commands"] = QJsonArray::fromStringList(commands);
      result["scene"]    = scene;
      respond(result);
      return;
   }

   if (cmd == "load") {
      const QString path(args.value("path").toString());
      if (path.isEmpty()) {
         fail("BAD_ARGS", "path required");
         return;
      }

      QFileInfo info(path);
      if (!info.exists()) {
         fail("LOAD_FAILED", QString("no such file: %1").arg(path));
         return;
      }
      if (!info.isFile()) {
         fail("LOAD_FAILED", QString("not a regular file: %1").arg(path));
         return;
      }

      MainWindow* mw(findMainWindow());
      if (!mw) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }

      m_controlBusy = true;

      bool opened(false);
      QEventLoop loop;
      QMetaObject::Connection conn = QObject::connect(&mw->viewerModel(),
         &ViewerModel::fileOpened, &loop, [&loop, &opened]() {
            opened = true; loop.quit();
         });
      QTimer::singleShot(kLoadTimeoutMs, &loop, SLOT(quit()));

      mw->open(info.absoluteFilePath());
      loop.exec();
      // The loop can be left by the timeout with the file still parsing; drop
      // the connection so a later success does not fire into a dead lambda.
      QObject::disconnect(conn);

      m_controlBusy = false;

      if (!opened) {
         fail("LOAD_FAILED", "the file did not open within the time limit");
         return;
      }

      QJsonObject result;
      result["path"]      = info.absoluteFilePath();
      result["loaded"]    = true;
      result["molecules"] = mw->viewerModel().moleculeList(false).size();
      respond(result);
      return;
   }

   // Snapshot: render the current scene to an image inside a confined directory.
   // Only the file name is taken from the request, never a path - the channel
   // must not be able to write anywhere the user did not already own.
   if (cmd == "snapshot") {
      MainWindow* mw(findMainWindow());
      if (!mw || !mw->viewer()) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }

      const QJsonValue outValue(args.value("out"));
      if (!outValue.isUndefined() && !outValue.isString()) {
         fail("BAD_ARGS", "out must be a string");
         return;
      }
      QString name(outValue.toString());
      if (name.isEmpty()) name = "snapshot.png";
      name = QFileInfo(name).fileName();            // drop any directory part
      // The channel is reachable by every process of this user; restrict the
      // name so one of them cannot clobber files the user made by hand.
      static const QRegularExpression allowedName(
         QStringLiteral("^[A-Za-z0-9][A-Za-z0-9._-]{0,59}\\.(png|jpg)$"),
         QRegularExpression::CaseInsensitiveOption);
      if (!allowedName.match(name).hasMatch()) {
         name += ".png";
         if (!allowedName.match(name).hasMatch()) {
            fail("BAD_ARGS",
                 "out must be 1-60 chars of [A-Za-z0-9._-] followed by .png or .jpg");
            return;
         }
      }

      // A non-numeric width/height would silently fall back to 0 and then be
      // clamped to 64, so reject it explicitly instead.
      for (const char* key : {"width", "height"}) {
         const QJsonValue v(args.value(key));
         if (!v.isUndefined() && !v.isDouble()) {
            fail("BAD_ARGS", QString("%1 must be a number").arg(key));
            return;
         }
      }
      const int width (qBound(64, args.value("width").toInt(1200), 4096));
      const int height(qBound(64, args.value("height").toInt(900), 4096));

      QDir dir(QDir(QStandardPaths::writableLocation(QStandardPaths::TempLocation))
               .filePath("iqmol-snapshots"));
      if (!dir.exists() && !dir.mkpath(".")) {
         fail("SNAPSHOT_FAILED", QString("cannot create %1").arg(dir.absolutePath()));
         return;
      }

      const QString path(dir.filePath(name));
      QFile::remove(path);
      mw->viewer()->saveImage(path, QSize(width, height), 96, 4);

      QFileInfo out(path);
      if (!out.exists() || out.size() == 0) {
         fail("SNAPSHOT_FAILED", "the renderer produced no image");
         return;
      }

      QJsonObject result;
      result["path"]   = out.absoluteFilePath();
      result["width"]  = width;
      result["height"] = height;
      result["bytes"]  = (qint64)out.size();
      respond(result);
      return;
   }

   // ------------------------------------------------------------------
   // Animation. There is no global "animator()" - animators are pushed into
   // Viewer::m_animatorList by Frequency/GeometryList layers through the
   // viewerModel's pushAnimators signal. So the honest way to control them is
   // to drive those layers, and let them start/stop the QGLViewer timer.
   // ------------------------------------------------------------------
   if (cmd == "play" || cmd == "pause" || cmd == "stop") {
      MainWindow* mw(findMainWindow());
      if (!mw) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }

      const bool enable(cmd == "play");
      int affected(0);

      QList<Layer::Frequencies*> freqLayers(
         mw->viewerModel().controlFindLayers<Layer::Frequencies>(kSceneLayers));
      for (Layer::Frequencies* f : freqLayers) {
         f->setPlay(enable);
         if (cmd == "stop") f->clearActiveMode();
         ++affected;
      }

      // GeometryList::setPlay/resetGeometry are protected slots; the meta
      // object ignores access control, so invoke by name rather than casting.
      QList<Layer::GeometryList*> geomLists(
         mw->viewerModel().controlFindLayers<Layer::GeometryList>(kSceneLayers));
      for (Layer::GeometryList* g : geomLists) {
         QMetaObject::invokeMethod(g, "setPlay", Q_ARG(bool, enable));
         if (cmd == "stop") QMetaObject::invokeMethod(g, "resetGeometry");
         ++affected;
      }

      // play is started by the layers' pushAnimators(); but QGLViewer only
      // stops its timer when the last animator is popped. If several layers
      // are animating, pause must stop the loop explicitly.
      if (mw->viewer() && !enable) mw->viewer()->stopAnimation();

      QJsonObject result;
      result["playing"]    = enable;
      result["animations"] = affected;
      result["timer"]      = mw->viewer() ? mw->viewer()->animationIsStarted() : false;
      if (affected == 0) {
         result["hint"] = "no animation data in the current scene "
                          "(needs a frequency calculation or a geometry trajectory)";
      }
      respond(result);
      return;
   }

   // frame: setCurrentGeometry() indexes the GeometryList's child rows, so
   // rowCount() (not the data list size) is the valid index space here.
   // Without "n" this is a read-only query that reports every trajectory.
   if (cmd == "frame") {
      MainWindow* mw(findMainWindow());
      if (!mw) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }
      const QJsonValue nValue(args.value("n"));
      const bool setFrame(!nValue.isUndefined());
      if (setFrame && !nValue.isDouble()) {
         fail("BAD_ARGS", "n must be an integer");
         return;
      }
      const QJsonValue trackValue(args.value("track"));
      if (!trackValue.isUndefined() && !trackValue.isDouble()) {
         fail("BAD_ARGS", "track must be an integer");
         return;
      }
      const int track(qBound(0, trackValue.toInt(0), 10000));

      QList<Layer::GeometryList*> geomLists(
         mw->viewerModel().controlFindLayers<Layer::GeometryList>(kSceneLayers));
      if (geomLists.isEmpty()) {
         fail("NO_FRAMES", "current scene has no geometry trajectory");
         return;
      }

      QJsonArray tracks;
      for (Layer::GeometryList* gl : geomLists) tracks.append(gl->rowCount());

      QJsonObject result;
      result["tracks"] = tracks;
      result["count"]  = tracks.size();
      if (!setFrame) { respond(result); return; }

      if (track >= geomLists.size()) {
         fail("BAD_ARGS", QString("track must be 0..%1")
                             .arg(geomLists.size() - 1));
         return;
      }
      Layer::GeometryList* g(geomLists.at(track));
      const int count(g->rowCount());
      if (count == 0) {
         fail("NO_FRAMES", "geometry trajectory is empty");
         return;
      }
      const int requested(nValue.toInt());
      const int frame(qBound(0, requested, count - 1));
      g->setCurrentGeometry((unsigned)frame);

      result["track"]     = track;
      result["frame"]     = frame;
      result["frames"]    = count;
      result["requested"] = requested;
      if (frame != requested) result["clamped"] = true;
      respond(result);
      return;
   }

   if (cmd == "listSurfaces") {
      MainWindow* mw(findMainWindow());
      if (!mw) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }
      QJsonArray surfaces(describeSurfaces(mw));
      QJsonObject result;
      result["surfaces"] = surfaces;
      result["count"]    = surfaces.size();
      respond(result);
      return;
   }

   // surface: the three pseudo densities that need no external cube/grid data.
   // Orbital/density surfaces require a Grid evaluator and stay unsupported.
   if (cmd == "surface") {
      MainWindow* mw(findMainWindow());
      if (!mw) {
         fail("NOT_READY", "main window is not up yet, retry in a moment");
         return;
      }
      const QString type(args.value("type").toString().toLower());
      const QMap<QString, Data::SurfaceType::Kind> kinds(surfaceKinds());
      if (!kinds.contains(type)) {
         fail("BAD_ARGS", "type must be one of vdw, promolecule, sid "
                          "(orbital/density need grid data and are unsupported)");
         return;
      }
      for (const char* key : {"quality", "iso"}) {
         if (!args.value(key).isUndefined() && !args.value(key).isDouble()) {
            fail("BAD_ARGS", QString("%1 must be a number").arg(key));
            return;
         }
      }
      const unsigned quality(static_cast<unsigned>(
         qBound(0, args.value("quality").toInt(3), 5)));
      const double iso(args.value("iso").toDouble(0.02));

      QList<Layer::MolecularSurfaces*> parents(
         mw->viewerModel().controlFindLayers<Layer::MolecularSurfaces>(kSceneLayers));
      if (parents.isEmpty()) {
         fail("NO_SURFACE_LAYER", "no molecule with atoms in the current scene");
         return;
      }

      Data::SurfaceInfo info(Data::SurfaceType(kinds.value(type)), quality, iso);
      m_controlBusy = true;
      parents.first()->requestSurface(info);
      m_controlBusy = false;

      QJsonArray surfaces(describeSurfaces(mw));
      QJsonObject result;
      result["type"]     = type;
      result["quality"]  = static_cast<int>(quality);
      result["iso"]      = iso;
      result["count"]    = surfaces.size();
      result["surfaces"] = surfaces;
      respond(result);
      return;
   }

   fail("NOT_IMPLEMENTED", "this command is not wired up in this build");
}


void IQmolApplication::loadTranslations()
{
   // 计算目标 locale。三态偏好(见 Preferences::Language 注释):
   //   "en"     -> 强制英文
   //   "zh_CN"  -> 强制中文
   //   "system" -> 跟随系统(系统非中文时, 应用自身翻译文件不存在则自然回退英文)
   //   未设置    -> 首次运行: 保持汉化默认, 非中文环境也显示中文
   QString locale = QLocale::system().name();
   QString pref = Preferences::Language();
   if (pref == "en") {
      locale = QString("en");
   } else if (pref == "zh_CN") {
      locale = QString("zh_CN");
   } else if (pref == "system") {
      // 保留系统 locale; 若无对应翻译文件, 下面加载会失败并回退英文
   } else if (!locale.startsWith("zh")) {
      locale = QString("zh_CN");   // 首次运行: 汉化默认
   }

   // Qt 基础翻译（标准对话框按钮等），跟随最终 locale。
   // 部署包中 Qt 安装目录不存在, 优先从程序目录 translations/ 加载
   // 随包分发的 qt_zh_CN.qm / qtbase_zh_CN.qm（由 deploy_windows.sh 复制）,
   // 开发环境再回退 Qt 安装目录。
   m_qtTranslator = new QTranslator(this);
   QString qtBasePath = QLibraryInfo::location(QLibraryInfo::TranslationsPath);
   QStringList qtSearchPaths;
   qtSearchPaths << QApplication::applicationDirPath() + "/translations"
                 << qtBasePath;
   bool qtLoaded(false);
   foreach (QString const& path, qtSearchPaths) {
      if (m_qtTranslator->load("qt_" + locale, path) ||
          m_qtTranslator->load("qtbase_" + locale, path)) {
         qtLoaded = true;
         break;
      }
   }
   if (qtLoaded) {
      installTranslator(m_qtTranslator);
   }

   // 应用翻译（IQmol 界面字符串）
   m_appTranslator = new QTranslator(this);

   // 依次尝试多个候选路径。
   //
   // [i18n] 注意 applicationDirPath() 是**可执行文件所在目录**，
   //   而不同平台的打包布局不同，qm 的相对位置也不同：
   //     Windows : bin/IQmol        + bin/translations/zh_CN.qm   （deploy_windows.sh）
   //     Linux   : bin/IQmol        + translations/zh_CN.qm       （包根，run.sh 布局）
   //   早期只搜 bin/translations 与 cwd，导致 Linux 包**只有恰好
   //   从包根目录启动时才加载成功**（偶然命中 cwd/translations），
   //   从桌面图标或 run.sh 之外的路径启动都会静默回退英文。
   //   故这里显式补上「可执行文件上一级的 translations/」。
   QString const appDir(QApplication::applicationDirPath());
   QStringList searchPaths;
   searchPaths << appDir + "/translations"            // Windows: bin/translations/
               << appDir + "/../translations"         // Linux  : 包根 translations/
               << appDir + "/../share/iqmol/translations"  // 系统安装布局兜底
               << appDir
               << QDir::current().filePath("translations")
               << QDir::currentPath();

   // 去重并剔除不存在的目录，避免 QTranslator 反复做无谓的 stat
   QStringList probePaths;
   foreach (QString const& p, searchPaths) {
      QString clean(QDir::cleanPath(p));
      if (!probePaths.contains(clean)) probePaths << clean;
   }

   bool loaded(false);
   foreach (QString const& path, probePaths) {
      if (m_appTranslator->load("IQmol_" + locale, path)) {
         loaded = true;
         break;
      }
   }
   // 也尝试不带前缀的文件名（与 lrelease 输出 zh_CN.qm 对应）
   if (!loaded) {
      foreach (QString const& path, probePaths) {
         if (m_appTranslator->load(locale, path)) {
            loaded = true;
            break;
         }
      }
   }
   if (loaded) {
      installTranslator(m_appTranslator);
      QLOG_INFO() << "Loaded translation:" << locale;
      qDebug() << "[i18n] Loaded translation:" << locale;
   } else {
      // 加载失败时把搜过的路径一并打出来，便于用户/打包方自查
      QLOG_INFO() << "No translation file found for:" << locale
                  << "searched:" << probePaths.join(", ");
      qDebug() << "[i18n] No translation file found for:" << locale;
      qDebug() << "[i18n] searched paths:" << probePaths;
   }
}


IQmolApplication::~IQmolApplication()
{
// This seems to cause a crash on exit under windows
//   if (m_splashScreen) delete m_splashScreen;
}


void IQmolApplication::showSplash()
{  
    QPixmap pixmap(":resources/splash.png");
    m_splashScreen = new QSplashScreen(pixmap);
    m_splashScreen->show();
    processEvents();
}


void IQmolApplication::hideSplash()
{  
   if (m_splashScreen) m_splashScreen->close();
}



void IQmolApplication::queueOpenFiles(QStringList const& files)
{
   QStringList::const_iterator iter;
   for (iter = files.begin(); iter != files.end(); ++iter) {
       FileOpenEvent* event = new FileOpenEvent(*iter);
       QApplication::postEvent(this, event, Qt::LowEventPriority);
   }
}


void IQmolApplication::initOpenBabel()
{
   QDir dir(QApplication::applicationDirPath());
   QString path;

#ifdef Q_OS_MAC
   // Assumed directory structure: IQmol.app/Contents/MacOS/IQmol
   dir.cdUp();  
   path = dir.absolutePath();
   QApplication::addLibraryPath(path + "/Frameworks");
   QApplication::addLibraryPath(path + "/PlugIns");
#endif

#ifdef Q_OS_WIN32
   // Assumed directory structure: IQmol/bin/IQmol
   dir.cdUp();  
   path = dir.absolutePath();
   QApplication::addLibraryPath(path + "/lib");
   QApplication::addLibraryPath(path + "/lib/plugins");
#endif

#ifdef Q_OS_LINUX
   // Assumed directory structure: IQmol/IQmol
   // This is so that when the executable is created it can be 
   // run from the main IQmol directory 
   path = dir.absolutePath();
   QApplication::addLibraryPath(path + "/lib");
   QApplication::addLibraryPath(path + "/lib/plugins");
#endif
   

   // This is not used any more as we ship with a static
   // version of OpenBabel
   QString env(qgetenv("BABEL_LIBDIR"));
   if (env.isEmpty()) {
#if defined(Q_OS_LINUX)
      // [reA22A] 便携分发包布局：优先探测可执行文件旁边的 OpenBabel
      // 插件目录（包根 lib/openbabel/<版本>/），解压即用、不依赖系统
      // 安装；找不到再回退系统路径（deb 包布局），保持历史行为兜底。
      QDir plugDir(path + "/../lib/openbabel");
      if (plugDir.exists()) {
         QStringList subs(plugDir.entryList(QDir::Dirs | QDir::NoDotAndDotDot));
         env = subs.isEmpty() ? plugDir.absolutePath()
                              : plugDir.absoluteFilePath(subs.first());
      } else {
         env = "/usr/lib/openbabel/3.1.1";
      }
#else
      env = path + "/lib/openbabel";
#endif
      qputenv("BABEL_LIBDIR", env.toLatin1());
      QLOG_INFO() << "Setting BABEL_LIBDIR = " << env;
   }else {
      QLOG_INFO() << "BABEL_LIBDIR already set: " << env;
   }

   env = qgetenv("BABEL_DATADIR");
   if (env.isEmpty()) {
#if defined(Q_OS_LINUX)
      // [reA22A] 同上：便携包优先用包根 share/openbabel，
      // 回退 deb 安装布局的系统路径。
      QString dataDir(path + "/../share/openbabel");
      env = QDir(dataDir).exists() ? dataDir : QString("/usr/share/openbabel");
#else
      env = path + "/share/openbabel";
#endif
      qputenv("BABEL_DATADIR", env.toLatin1());
      QLOG_INFO() << "Setting BABEL_DATADIR = " << env;
   }else {
      QLOG_INFO() << "BABEL_DATADIR already set: " << env;
   }


}


void IQmolApplication::open(QString const& file)
{
   // This is the first thing that is called once the event loop has started,
   // even if there is no actual file to open (empty file name).  This is an
   // ideal time to check if OpenBabel is around.  
   initOpenBabel();

   MainWindow* mw;
   QWidget* window(QApplication::activeWindow());
   if ( !(mw = qobject_cast<MainWindow*>(window)) ) {
      mw = new MainWindow();
      connect(mw, SIGNAL(quit()), this, SLOT(quitRequest()));
      QApplication::setActiveWindow(mw);
   }

   QFileInfo info(file);
   if (info.exists()) mw->open(file);
   hideSplash();
   mw->show();
   mw->raise();

   // Now we can load jobs from the preferences, if we try to do it 
   // before now, the dialog appears under the splash screen
   Process::JobMonitor::instance().loadJobListFromPreferences();
   
   static bool connected(false);
   if (!connected) {
      connect(this, SIGNAL(lastWindowClosed()), this, SLOT(quitRequest()));
      connected = true;
   }
   QLOG_INFO() << "Number of threads:" << QThread::idealThreadCount();
   QLOG_INFO() << "Active    threads:" << QThreadPool::globalInstance()->activeThreadCount();
}


bool IQmolApplication::event(QEvent* event)
{
   bool accepted(false);

   switch (event->type()) {
      case QEvent::FileOpen: {
         QString file(static_cast<QFileOpenEvent*>(event)->file());
         queueOpenFiles(QStringList(file));
         accepted = true;
         } break;

      case QEvent::User: {
         QString file(static_cast<FileOpenEvent*>(event)->file());
         open(file);
         accepted = true;
         } break;

      default:
         accepted = QApplication::event(event);
         break;
   }

   return accepted;
}


void IQmolApplication::quitRequest()
{
   Process::ServerRegistry::instance().closeAllConnections();
   QApplication::quit();  
}


void IQmolApplication::exception()
{
   m_unhandledException.exec();   
}


} // end namespace IQmol
