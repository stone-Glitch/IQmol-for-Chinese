// ctxprobe.C —— 用真实 Qt QTranslator 探测 .qm 中各 context 的命中情况
//
// 为什么需要它：Qt 的 tr() 在运行时按「类名（含 namespace）」查表，
// 而 lupdate 写进 .ts 的 context 名不一定与之一致。
// 静态分析（读 .ts / 读源码）只能推断，这个程序给出**运行时真相**。
//
// 编译：见同目录 build_ctxprobe.sh
// 用法：./ctxprobe <zh_CN.qm> ["context<TAB>source" ...]

#include <QCoreApplication>
#include <QTranslator>
#include <QStringList>
#include <QDebug>
#include <cstdio>

int main(int argc, char** argv)
{
   QCoreApplication app(argc, argv);

   QStringList args = app.arguments();
   if (args.size() < 2) {
      fprintf(stderr, "用法: %s <qm文件> [context:source ...]\n", qPrintable(args[0]));
      return 2;
   }

   QTranslator tr;
   if (!tr.load(args[1])) {
      fprintf(stderr, "加载失败: %s\n", qPrintable(args[1]));
      return 2;
   }
   printf("已加载: %s\n\n", qPrintable(args[1]));

   // 待探测的 (context, source) 组合。
   // ⚠️ context 名本身含 '::'（如 IQmol::Layer::Atom），
   //    所以分隔符**不能**用 ':'，改用 '\t'。
   QList<QPair<QString, QString> > probes;
   for (int i = 2; i < args.size(); ++i) {
      int k = args[i].indexOf('\t');
      if (k < 0) continue;
      probes.append(qMakePair(args[i].left(k), args[i].mid(k + 1)));
   }
   if (probes.isEmpty()) {
      // 默认探针：截图里出现英文的那批
      probes.append(qMakePair(QString("Qui::InputDialog"), QString("File")));
      probes.append(qMakePair(QString("InputDialog"),     QString("File")));
      probes.append(qMakePair(QString("Qui::InputDialog"), QString("Job")));
      probes.append(qMakePair(QString("InputDialog"),     QString("Job")));
      probes.append(qMakePair(QString("Qui::InputDialog"), QString("Font")));
      probes.append(qMakePair(QString("InputDialog"),     QString("Font")));
      probes.append(qMakePair(QString("MainWindow"),      QString("SCF Control")));
      probes.append(qMakePair(QString("MainWindow"),      QString("Algorithm")));
      probes.append(qMakePair(QString("IQmol::MainWindow"), QString("File")));
   }

   printf("%-26s %-22s %s\n", "context", "source", "结果");
   printf("%s\n", QByteArray(78, '-').constData());
   for (int i = 0; i < probes.size(); ++i) {
      const QString& ctx = probes[i].first;
      const QString& src = probes[i].second;
      QString hit = tr.translate(ctx.toUtf8().constData(),
                                 src.toUtf8().constData());
      bool ok = !hit.isEmpty();
      printf("%-26s %-22s %s\n",
             qPrintable(ctx), qPrintable(src),
             ok ? qPrintable("✅ " + hit) : "❌ 未命中（回退英文）");
   }
   return 0;
}
