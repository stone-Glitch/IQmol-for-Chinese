// 验证 zh_CN.qm 能否被 QTranslator 正确加载
#include <QApplication>
#include <QTranslator>
#include <QCoreApplication>
#include <QLibraryInfo>
#include <QDebug>
#include <QDir>

int main(int argc, char *argv[])
{
   QApplication app(argc, argv);
   QCoreApplication::setOrganizationDomain("iqmol.org");
   QCoreApplication::setApplicationName("IQmol");

   QTranslator translator;
   QString locale = QLocale::system().name();
   if (!locale.startsWith("zh")) locale = QString("zh_CN");

   QStringList paths;
   paths << QApplication::applicationDirPath() + "/translations"
         << QApplication::applicationDirPath()
         << QDir::current().filePath("translations")
         << QDir::currentPath();
   paths << argv[1]; // 也允许直接传入 ts/qm 所在目录

   bool loaded(false);
   foreach (QString const& path, paths) {
      if (translator.load("IQmol_" + locale, path)) { loaded = true; qDebug() << "Loaded IQmol_zh_CN from:" << path; break; }
   }
   if (!loaded) {
      foreach (QString const& path, paths) {
         if (translator.load(locale, path)) { loaded = true; qDebug() << "Loaded zh_CN from:" << path; break; }
      }
   }

   if (!loaded) {
      qDebug() << "FAILED to load translation";
      return 1;
   }

   app.installTranslator(&translator);

   // 逐条验证关键翻译
   struct { const char* src; const char* expected; } checks[] = {
      {"File", "文件"},
      {"About", "关于"},
      {"Save Changes?", "保存更改？"},
      {"Welcome to IQmol", "欢迎使用 IQmol"},
      {"Atom Labels", "原子标签"},
      {"Minimize Structure", "结构最小化"},
      {"Show Message Log", "显示消息日志"},
      {"Use <esc> to exit full screen mode", "按 Esc 退出全屏模式"},
      {"Wonky molecule detected", "检测到异常分子"},
      {"Do you want to proceed?", "是否继续？"},
   };

   int fail = 0;
   for (unsigned i = 0; i < sizeof(checks)/sizeof(checks[0]); ++i) {
      QString t = QCoreApplication::translate("IQmol::MainWindow", checks[i].src);
      bool ok = (t == QString::fromUtf8(checks[i].expected));
      qDebug() << (ok ? "PASS" : "FAIL") << checks[i].src << "->" << t;
      if (!ok) fail++;
   }

   qDebug() << "Total failures:" << fail;
   return fail ? 1 : 0;
}
