// ---------------------------------------------------------------------------
//  ControlServer.C
//
//  See ControlServer.h for the protocol and the design rules.
//
//  Compiles against Qt5 (IQmol3's baseline). If your fork has moved to Qt6,
//  the only changes needed are:
//      QJsonDocument / QLocalServer / QUuid  -> unchanged
//      QStandardPaths::RuntimeLocation       -> unchanged
//      qrand / QRandomGenerator              -> not used here
// ---------------------------------------------------------------------------

#include "ControlServer.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocalServer>
#include <QLocalSocket>
#include <QProcessEnvironment>
#include <QStandardPaths>
#include <QUuid>

#include <cstdio>

namespace IQmol {

namespace {
   const int    kProtocolVersion = 1;
   const char*  kServerName      = "iqmol-ctrl";
   const qint64 kMaxFrameBytes   = 1 << 20;   // 1 MiB: a command is never big

   // A crashed instance can leave its socket behind. Binding over it is only
   // safe if nobody is listening, otherwise we would steal a live instance's
   // endpoint. Note QLocalServer::listen() would remove the stale file itself,
   // so this check has to happen first.
   bool socketIsStale(QString const& path)
   {
      if (!QFile::exists(path)) return true;
      QLocalSocket probe;
      probe.connectToServer(path);
      if (probe.waitForConnected(300)) {
         probe.disconnectFromServer();
         return false;                     // somebody is alive on it
      }
      return true;
   }
}


ControlServer::ControlServer(QObject* parent)
   : QObject(parent), m_server(nullptr), m_bound(false)
{
}


ControlServer::~ControlServer()
{
   stop();
}


QSet<QString> ControlServer::allowedCommands()
{
   // PR2: view control. PR3 (headless batch render) will add "render" and
   // "movie".
   //
   // Anything not in this set is dropped without a reply - see rule 4 in the
   // header. Note what is deliberately absent: nothing here closes the app,
   // changes preferences, submits a job, or writes outside a whitelisted
   // directory. Those are user actions and stay that way.
   QSet<QString> cmds;
   cmds << "ping"
        << "load"
        << "state"
        << "play"           // {what: "vibration"|"reaction"|"optimization"}
        << "pause"
        << "stop"
        << "frame"          // {n: int}
        << "surface"        // {type:"orbital"|"density", index, iso}
        << "listSurfaces"
        << "snapshot";      // {out: filename, width, height} - confined dir
   return cmds;
}


QString ControlServer::runtimeDir() const
{
   // Both ends must agree on this directory, so do not simply delegate to
   // QStandardPaths::RuntimeLocation. With XDG_RUNTIME_DIR set (the normal
   // desktop case: /run/user/1000) Qt and a Node client agree. Without it,
   // Qt falls back to /tmp/runtime-<user> while a Node client (os.tmpdir())
   // falls back to /tmp, and the client would never find us - so we pick the
   // temp dir ourselves in that case.
   const QByteArray xdg(qgetenv("XDG_RUNTIME_DIR"));
   if (!xdg.isEmpty()) return QString::fromLocal8Bit(xdg);

   QString dir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
   if (dir.isEmpty()) dir = QDir::tempPath();
   if (dir.isEmpty()) dir = QDir::homePath() + "/.iqmol";
   return dir;
}


bool ControlServer::start(QString* error)
{
   if (m_server) return true;

   const QString dir = runtimeDir();
   QDir().mkpath(dir);

#ifdef Q_OS_WIN
   // A bare name gives us \\.\pipe\iqmol-ctrl, which Node's net.connect can
   // open as \\.\pipe\iqmol-ctrl too.
   const QString endpoint = QString("\\\\.\\pipe\\%1").arg(kServerName);
   m_socketPath           = QString(kServerName);
#else
   // Absolute path on Unix so the socket lands somewhere predictable and the
   // client does not have to guess Qt's temp layout.
   m_socketPath = dir + "/" + QString(kServerName) + ".sock";
   const QString endpoint = m_socketPath;
#endif

   // Never evict a socket that is still bound, even if its path is gone (the
   // file removed by hand, or a crashed owner): QLocalServer would recreate the
   // path and silently drop the old listener, leaving a live app unreachable.
   // Only an unbound leftover file is safe to remove.
   if (!socketIsStale(m_socketPath)) {
      if (error) {
         *error = QString("another instance is already listening on %1")
                     .arg(m_socketPath);
      }
      return false;
   }
   QLocalServer::removeServer(m_socketPath);

   m_server = new QLocalServer(this);
   if (!m_server->listen(m_socketPath)) {
      const QString why = m_server->errorString();
      delete m_server;
      m_server = nullptr;
      if (error) {
         *error = QString("cannot listen on %1: %2").arg(m_socketPath).arg(why);
      }
      return false;
   }

   connect(m_server, &QLocalServer::newConnection,
           this, &ControlServer::onNewConnection);

   m_bound = true;

   m_token        = QUuid::createUuid().toString(QUuid::WithoutBraces);
   m_startedAt    = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
   m_endpointPath = dir + "/" + QString(kServerName) + ".json";

   // Publish discovery info. Written atomically and 0600: the token is the
   // only thing standing between a local process and control of this app.
   QJsonObject info;
   info["v"]         = kProtocolVersion;
   info["pid"]       = (qint64)QCoreApplication::applicationPid();
   info["endpoint"]  = endpoint;
   info["token"]     = m_token;
   info["startedAt"] = m_startedAt;

   QJsonArray cmds;
   QStringList allowed(allowedCommands().toList());
   allowed.sort();                       // stable output, QSet order is unspecified
   for (const QString& c : allowed) cmds.append(c);
   info["commands"] = cmds;

   const QByteArray body =
      QJsonDocument(info).toJson(QJsonDocument::Compact);

   const QString tmp = m_endpointPath + ".tmp";
   {
      QFile f(tmp);
      if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
         if (error) *error = QString("cannot write %1").arg(tmp);
         return false;   // listening, but unpublished - treat as failure
      }
      f.write(body);
      f.write("\n");
      f.close();
      f.setPermissions(QFile::ReadOwner | QFile::WriteOwner);
   }
   QFile::remove(m_endpointPath);
   if (!QFile::rename(tmp, m_endpointPath)) {
      if (error) *error = QString("cannot rename to %1").arg(m_endpointPath);
      return false;
   }
   QFile::setPermissions(m_endpointPath,
                         QFile::ReadOwner | QFile::WriteOwner);

   return true;
}


void ControlServer::setAllowedOutputDirs(const QStringList& dirs)
{
   m_outputDirs.clear();
   for (const QString& d : dirs) {
      if (d.isEmpty()) continue;
      // canonicalFilePath resolves symlinks; without it a link placed inside
      // an allowed directory would let a write land anywhere.
      m_outputDirs << QFileInfo(d).canonicalFilePath();
   }
}


bool ControlServer::outputAllowed(const QString& path) const
{
   if (path.isEmpty() || m_outputDirs.isEmpty()) return false;

   // A bare filename, nothing else. Rejecting separators here (rather than
   // relying on the directory check below) is what stops "sub/x.png" from
   // targeting a directory that does not exist, and stops a crafted name from
   // exploiting any future leniency in the join.
   if (path.contains('/') || path.contains('\\')) return false;
   if (path.contains("..")) return false;

   const QString target = QFileInfo(QDir::cleanPath(path)).absoluteFilePath();
   const QString parent = QFileInfo(target).absolutePath();
   const QString canonicalParent = QFileInfo(parent).canonicalFilePath();
   const QString check = canonicalParent.isEmpty() ? parent : canonicalParent;

   for (const QString& dir : m_outputDirs) {
      if (check == dir) return true;
   }
   return false;
}


void ControlServer::stop()
{
   // Only unlink what this instance actually bound. Without the guard a second
   // IQmol whose listen() failed would delete the *live* instance's socket on
   // destruction, and a hand-written client with the right token would then
   // start connecting to us instead of to the real owner.
   if (!m_bound) return;

   if (m_server) {
      m_server->close();
      delete m_server;
      m_server = nullptr;
   }
   if (!m_socketPath.isEmpty()) {
      QLocalServer::removeServer(m_socketPath);
   }
   if (!m_endpointPath.isEmpty()) {
      QFile::remove(m_endpointPath);
      m_endpointPath.clear();
   }
   m_buffers.clear();
   m_bound = false;
}


bool ControlServer::isListening() const
{
   return m_server && m_server->isListening();
}


void ControlServer::onNewConnection()
{
   while (QLocalSocket* client = m_server->nextPendingConnection()) {
      connect(client, &QLocalSocket::readyRead,
              this, &ControlServer::onReadyRead);
      connect(client, &QLocalSocket::disconnected,
              this, &ControlServer::onDisconnected);
      m_buffers.insert(client, QByteArray());
   }
}


void ControlServer::onDisconnected()
{
   QLocalSocket* client = qobject_cast<QLocalSocket*>(sender());
   if (!client) return;
   m_buffers.remove(client);
   client->deleteLater();
}


void ControlServer::onReadyRead()
{
   QLocalSocket* client = qobject_cast<QLocalSocket*>(sender());
   if (!client) return;

   if (!m_buffers.contains(client)) m_buffers.insert(client, QByteArray());
   m_buffers[client].append(client->readAll());

   // A slow or hostile writer must not grow the buffer without bound.
   if (m_buffers[client].size() > kMaxFrameBytes) {
      m_buffers[client].clear();
      client->disconnectFromServer();
      return;
   }

   bool gotOne = true;
   while (gotOne) {
      const QByteArray frame = takeFrame(client, gotOne);
      // handleFrame may disconnect (bad token) and the socket then emits
      // disconnected(); anything queued after that must not touch it again.
      if (!gotOne || client->state() == QLocalSocket::UnconnectedState) break;
      handleFrame(client, frame);
   }
}


QByteArray ControlServer::takeFrame(QLocalSocket* client, bool& gotOne)
{
   QByteArray& buf = m_buffers[client];
   const int nl = buf.indexOf('\n');
   if (nl < 0) { gotOne = false; return QByteArray(); }
   QByteArray frame = buf.left(nl);
   buf.remove(0, nl + 1);
   gotOne = true;
   return frame;
}


bool ControlServer::authorised(const QJsonObject& req) const
{
   // Constant-time-ish compare is pointless against a local socket guarded by
   // file permissions, but we still never compare against an empty token.
   if (m_token.isEmpty()) return false;
   return req.value("token").toString() == m_token;
}


void ControlServer::handleFrame(QLocalSocket* client, const QByteArray& raw)
{
   QJsonParseError parseError;
   const QJsonDocument doc = QJsonDocument::fromJson(raw, &parseError);
   // Best effort id so the client can correlate even a malformed reply. Keep the
   // JSON type as sent: clients commonly use integers, and toString() would turn
   // those into an empty string that no longer matches the request.
   QJsonValue id = QJsonValue(QString());
   if (doc.isObject()) {
      const QJsonValue candidate(doc.object().value("id"));
      // An object/array id would make every reply bigger than the request;
      // fall back to null so the client still gets a well-formed answer.
      if (candidate.isString() || candidate.isDouble() || candidate.isBool() ||
          candidate.isNull()) {
         id = candidate;
      }
   }

   if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
      reject(client, id, "BAD_JSON", "request is not a JSON object");
      return;
   }

   const QJsonObject req = doc.object();

   if (req.value("v").toInt() != kProtocolVersion) {
      reject(client, id, "BAD_VERSION",
             QString("protocol version must be %1").arg(kProtocolVersion));
      return;
   }

   // Rule 4: no response at all for unauthorised frames. An unauthenticated
   // local process learns nothing - not even that we exist.
   if (!authorised(req)) {
      client->disconnectFromServer();
      return;
   }

   const QString cmd = req.value("cmd").toString();
   if (!allowedCommands().contains(cmd)) {
      reject(client, id, "BAD_COMMAND", "command not supported");
      return;
   }

   emit commandReceived(client, req);
}


void ControlServer::reject(QLocalSocket* client, const QJsonValue& id,
                           const QString& code, const QString& message)
{
   QJsonObject err;
   err["code"]    = code;
   err["message"] = message;

   QJsonObject res;
   res["v"]  = kProtocolVersion;
   res["id"] = id;
   res["ok"] = false;
   res["error"] = err;

   sendResponse(client, res);
}


void ControlServer::sendResponse(QLocalSocket* client, const QJsonObject& response)
{
   if (!client) return;
   const QByteArray out =
      QJsonDocument(response).toJson(QJsonDocument::Compact) + "\n";
   client->write(out);
   client->flush();
}

} // end namespace IQmol
