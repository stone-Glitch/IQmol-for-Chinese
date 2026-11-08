// ---------------------------------------------------------------------------
//  ControlServer.h
//
//  A minimal, local-only control channel for IQmol.
//
//  Design constraints that shaped this file - do not "simplify" them away:
//
//   1. Local only. QLocalServer is a Unix domain socket on Linux/macOS and a
//      named pipe on Windows. Nothing here binds a TCP port, so nothing here
//      is reachable from the network.
//
//   2. Token gated. A random token is generated per process and written to a
//      0600 file. A client that cannot read that file cannot talk to us.
//
//   3. This class knows NOTHING about molecules, viewers or layers. It parses
//      frames, rejects anything off the whitelist, and emits a signal. Every
//      real action lives in the owner (IQmolApplication). That keeps the
//      blast radius of this patch to one signal connection.
//
//   4. Whitelist, not reflection. Unknown commands are dropped silently. We
//      deliberately do not tell the client which commands exist.
//
//  Wire protocol (newline-delimited JSON, one object per line):
//
//      -> {"v":1,"id":"<uuid>","token":"<hex>","cmd":"load","args":{...}}
//      <- {"v":1,"id":"<uuid>","ok":true,"result":{...}}
//      <- {"v":1,"id":"<uuid>","ok":false,"error":{"code":"...","message":"..."}}
//
//  Namespace matches IQmol3. If your fork renamed it, adjust consistently.
// ---------------------------------------------------------------------------

#ifndef IQMOL_CONTROLSERVER_H
#define IQMOL_CONTROLSERVER_H

#include <QFileInfo>
#include <QHash>
#include <QJsonObject>
#include <QObject>
#include <QSet>
#include <QString>
#include <QStringList>

class QLocalServer;
class QLocalSocket;

namespace IQmol {

class ControlServer : public QObject
{
   Q_OBJECT

   public:
      explicit ControlServer(QObject* parent = nullptr);
      ~ControlServer() override;

      // Bring the channel up. Returns false (with a reason) rather than
      // throwing - a failed control channel must never stop IQmol starting.
      bool start(QString* error = nullptr);
      void stop();
      bool isListening() const;

      // Discovery: clients read this file to find us.
      QString endpointPath() const { return m_endpointPath; }
      QString socketPath()   const { return m_socketPath; }
      QString token()        const { return m_token; }
      QString startedAt()    const { return m_startedAt; }

      // Confinement for the commands that WRITE files (snapshot). An empty
      // list refuses every write, which is the safe default before the owner
      // has configured one. Symlinks are resolved, so a link inside an
      // allowed directory cannot be used to escape it.
      void setAllowedOutputDirs(const QStringList& dirs);
      bool outputAllowed(const QString& path) const;

      // The owner calls this once it has finished handling a request.
      void sendResponse(QLocalSocket* client, const QJsonObject& response);

      // Commands accepted by this revision of the skeleton.
      static QSet<QString> allowedCommands();

   signals:
      // Emitted only for whitelisted, token-valid requests.
      void commandReceived(QLocalSocket* client, QJsonObject request);

   private slots:
      void onNewConnection();
      void onReadyRead();
      void onDisconnected();

   private:
      QByteArray takeFrame(QLocalSocket*, bool& gotOne);
      void handleFrame(QLocalSocket*, const QByteArray& raw);
      void reject(QLocalSocket*, const QJsonValue& id, const QString& code,
                  const QString& message);
      bool authorised(const QJsonObject&) const;
      bool m_bound;          // did THIS instance bind the socket (see stop())
      QString runtimeDir() const;

      QLocalServer* m_server;
      QString m_socketPath;
      QString m_endpointPath;
      QString m_token;
      QString m_startedAt;
      QStringList m_outputDirs;
      QHash<QLocalSocket*, QByteArray> m_buffers;
};

} // end namespace IQmol

#endif // IQMOL_CONTROLSERVER_H
