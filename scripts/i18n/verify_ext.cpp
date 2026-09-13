// 全量验证：读取 zh_CN.ts 的真实 (context, source)，用 qm 加载后逐一核对译文
#include <QApplication>
#include <QTranslator>
#include <QXmlStreamReader>
#include <QFile>
#include <QDir>
#include <QTextStream>
#include <cstdio>

struct Entry { QString ctx; QString src; QString tr; };

int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    if (argc < 3) { fprintf(stderr, "用法: %s <qm目录> <zh_CN.ts>\n", argv[0]); return 1; }

    QTranslator appTr;
    QString qm = QDir(argv[1]).filePath("zh_CN.qm");
    if (!appTr.load(qm)) { fprintf(stderr, "加载失败: %s\n", qm.toUtf8().constData()); return 2; }
    app.installTranslator(&appTr);

    // 读取 ts
    QList<Entry> entries;
    QFile f(argv[2]);
    if (!f.open(QIODevice::ReadOnly)) { fprintf(stderr, "无法打开 ts\n"); return 2; }
    QXmlStreamReader xml(&f);
    QString curCtx, curSrc, curTr; bool inMsg=false, inSrc=false, inTr=false;
    while (!xml.atEnd()) {
        xml.readNext();
        if (xml.isStartElement()) {
            QString n = xml.name().toString();
            if (n == "context") { curCtx.clear(); }
            else if (n == "name") { curCtx = xml.readElementText(); }
            else if (n == "message") { inMsg=true; curSrc.clear(); curTr.clear(); }
            else if (n == "source" && inMsg) { curSrc = xml.readElementText(); }
            else if (n == "translation" && inMsg) { curTr = xml.readElementText(); }
        } else if (xml.isEndElement() && xml.name().toString() == "message") {
            if (!curSrc.isEmpty()) entries.append({curCtx, curSrc, curTr});
            inMsg=false;
        }
    }
    f.close();

    int pass=0, fail=0; QTextStream out(stdout);
    for (const Entry& e : entries) {
        QString got = app.translate(e.ctx.toUtf8().constData(), e.src.toUtf8().constData());
        if (got == e.tr) ++pass;
        else { ++fail; if (fail<=15) out << "[FAIL] ctx=" << e.ctx << " src=" << e.src
                    << " 期望[" << e.tr << "] 实际[" << got << "]\n"; }
    }
    out << QString("全量核对: %1 通过, %2 失败 (共 %3)\n").arg(pass).arg(fail).arg(entries.size());
    return fail ? 3 : 0;
}
