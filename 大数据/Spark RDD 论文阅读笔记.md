# 总结
## Spark 相关
### Spark 简要运行架构和计算原理
开发员需要写连接集群中的 workers 的 driver 程序来使用 spark，就比如图 2 展示的。Driver 端程序定义了一系列的 RDDs 并且调用了 RDD 的 action 操作。Driver 的程序同时也会跟踪 RDDs 之间的的血缘关系。workers 是可以将 RDD 分区数据存储在内存中的长期存活的进程。<br />![](https://cdn.nlark.com/yuque/0/2024/jpeg/2847893/1709542005833-de5a2647-2395-4c95-87c7-e4a53621bd04.jpeg#averageHue=%23f1eeee&clientId=u811617d4-f2d8-4&from=paste&id=asjIp&originHeight=472&originWidth=856&originalType=url&ratio=1&rotation=0&showTitle=false&status=done&style=none&taskId=u260bbee2-0114-4c0e-bf32-c942344e95b&title=)<br />在 2.2.1 小节中的日志挖掘例子中，我们提到，用户提供给 RDD 操作比如 map 以参数作为这个操作的闭包（说白了就是函数）。Scala 将这些函数看作一个 java 对象，这些对象是可以序列化的，并且可以通过网络传输传输到其他的机器节点上的。Scala 将函数中的变量看作一个对象中的变量。比如，我们可以写一段这样的代码：var x = 5; rdd.map（_ + 5）来达到给这个 RDD 每一个元素加上 5 的目的。

RDDs 是被一元素类型参数化的静态类型对象，比如，RDD[Int] 表示一个类型为整数的 RDD。然而，我们很多例子中的 RDD 都会省去这个类型，这个是因为 scala 支持类型推断。


### Spark 的提速点
#### 中间数据的存放方式
传统分布式计算框架对中间计算结果的保存是将中间文件写到一个稳定的系统中（例如分布式文件系统），以此来进行中间数据的广播和容错保证。这样做的缺点是**这样会由于数据的复制备份，磁盘的 **`**I/O**`** 以及数据的序列化而致应用任务执行很费时间。**
#### **其余的提速点**
理解为什么提速了：我们惊奇的发现 spark 甚至比基于内存存储二进制数据的 hadoopBinMem 还要快 20 倍。在 hadoopBinMem 中，我们使用的是 hadoop 标准的二进制文件格式（sequenceFile）和 256 m 这么大的数据块大小，以及我们强制将 hadoop 的数据目录放在一个内存的文件系统中。然而，Hadoop 仍然因为下面几点而比 spark 慢:

- Hadoop 软件栈的最低开销。
- HDFS 提供数据服务的开销。（因为每次中间文件都是落盘到 hdfs 上）
- 将二进制数据转换成有效的内存中的 java 对象的反序列化的成本开销。

我们依次来调查上面的每一个因素。为了测量第一个因素，我们跑了一些空的 hadoop 任务，我们发现单单完成 job 的设置、任务的启动以及任务的清理等工作就花掉了至少 25 秒钟。对于第二个元素，我们发现 HDFS 需要执行多份内存数据的拷贝以及为每一个数据块做 checksum 计算。<br />最后，为了测试第 3 个因素，我们在单机上做了一个微型的基准测试，就是针对不同文件类型的 256 M 数据来跑线性回归计算。我们特别的对比了分别从 HDFS 文件（HDFS 技术栈的耗时将会很明显）和本地内存文件（内核可以很高效的将数据传输给应用程序）中处理文本和二进制类型数据所话的时间、<br />图九中是我们我们测试结果的展示。从 In - memory HDFS（数据是在本地机器中的内存中）中读数据比从本地内存文件中读数据要多花费 2 秒中。解析文本文件要比解析二进制文件多花费 7 秒钟。最后，即使从本地内存文件中读数据，但是将预先解析了二进制数据转换成 java 对象也需要 3 秒钟，这个对于线性回归来说也是一个非常耗时的操作。Spark 将 RDDs 所有元素以 java 对象的形式存储在内存中，进而避免了上述说的所有的耗时<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/2847893/1709715190353-eea6f0ba-f5e9-463a-8d52-b9efd1503ad0.png#averageHue=%23f0efee&clientId=u52f16dad-c2fa-4&from=paste&height=346&id=ue10fe78b&originHeight=346&originWidth=645&originalType=binary&ratio=1&rotation=0&showTitle=false&size=29355&status=done&style=none&taskId=u9a700795-201a-41b1-95ad-135dec2493d&title=&width=645)
## RDD & RDDs
### RDDs 结构图
`RDDs` 是一个抽象的概念，其由多个 `RDD` 组成，蓝色框代表着一个 `RDD` ，蓝色色块代表着分区，一个 `RDD` 包含多个分区；连接线代表着 RDD & 分区间的依赖关系。<br />![image.png](https://cdn.nlark.com/yuque/0/2024/png/2847893/1709264545716-b4ffdda4-b14f-470a-b06f-f8b6d76b9042.png#averageHue=%23f3f2f2&clientId=u2fc4cad2-9317-4&from=paste&id=MLtom&originHeight=594&originWidth=904&originalType=url&ratio=1&rotation=0&showTitle=false&size=134371&status=done&style=none&taskId=u25609960-5960-4f5a-b4af-4422df6c5a4&title=)
### RDDs
`RDDs` 由 `RDD` 组成。
### RDD
#### RDD的结构
`RDD` 是一个数据对象的抽象，是一个可以容错且并行的结构。<br />一个 `RDD` 由多个分区（partition）组成，分区的指定可以自动设定也可以手动设定为范围分区或者 `hash` 分区。
#### **数据不可变特性**
`RDD` 具有数据不可变的特性，此特性带来了以下好处：

- 依赖此特性可以无需特意关注数据一致性来达成并行运算。
- 利用数据不可变性可以很方便的进行 checkpoint 而无需中止正在进行计算的程序。
- 通过并行运算可以很方便的通过备份任务来加速计算慢的任务。

内存不可变性带来了一定的限制，但是在大数据领域上，这种限制性在批处理上受到的影响很小。（为什么，补充下）
#### 血缘
`RDD` 其容错能力源于其对血缘关系的保存。每一个 `RDD` 都能清楚直到自身的每个分区该由哪个 `RDD` 的哪个分区推导而来，当检测出自身某个分区数据出错时，只需根据父 `RDD` 简单重算下该分区的数据即可；而且因为数据不可变的特性，该任务还可以在不同的节点上并行计算。
#### 适用场景
`RDD`适用于什么类型的任务？大批量分析的计算任务，需要数据复用的任务。不适用于频繁广播更新状态的应用，例如 web 服务。
### RDD 的内存管理
#### 对象的保存
> Spark provides three options for storage of persistent RDDs: in-memory storage as deserialized Java objects, in-memory storage as serialized data, and on-disk storage.
> Spark 提供了三种持久 RDDs 的存储选项：作为反序列化 Java 对象的内存存储、作为序列化数据的内存存储和磁盘存储。
> The first option provides the fastest performance, because the Java VM can access each RDD element natively. The second option lets users choose a more memory-efficient representation than Java object graphs when space is limited, at the cost of lower performance.(8) The third option is useful for RDDs that are too large to keep in RAM but costly to recompute on each use.
> 第一个选项提供最快的性能，因为 Java VM 可以本机访问每个 RDD 元素。 第二个选项允许用户在空间有限时选择比 Java 对象图更高效的表示形式，但代价是性能较低。(8) 第三个选项对于太大而无法保存在 RAM 中但每次使用时重新计算成本高昂的 RDD 很有用 。
> (8) The cost depends on how much computation the application does per byte of data, but can be up to 2× for lightweight processing.
> 成本取决于应用程序对每个数据字节执行的计算量，但对于轻量级处理而言，成本可能高达 2 倍。

Todo: 序列化存储 Java 对象为什么会更节省内存？这个序列化是指像 `Protobuf` 那样只将数据存储，而不将类结构（例如类变量和类函数之类的字节数据）相关数据存储吗？Java 图对象又是什么？
#### 内存回收
> To manage the limited memory available, we use an LRU eviction policy at the level of RDDs.
> 为了管理有限的可用内存，我们在 RDDs 层面上使用 LRU 回收策略。
> When a new RDD partition is computed but there is not enough space to store it, we evict a partition from the least recently accessed RDD, **unless this is the same RDD as the one with the new partition.**
> 当计算出新的 RDD 分区但没有足够的空间来存储它时，我们会从最近最少访问的 RDD 中逐出一个分区，**除非新计算出的分区与被逐出的分区属于同一个 RDD** 。
> In that case, we keep the old partition in memory to prevent cycling partitions from the same RDD in and out.
> 在这种情况下，我们将旧分区保留在内存中，以防止同一 RDD 中的分区循环进出（循环被计算）。
> This is important because most operations will run tasks over an entire RDD, so it is quite likely that the partition already in memory will be needed in the future.
> 这很重要，因为大多数操作将在整个 RDD 上运行任务，因此将来很可能需要内存中已有的分区。
> We found this default policy to work well in all our applications so far, but we also give users further control via a “persistence priority” for each RDD.
> 到目前为止，我们发现这个默认策略在我们所有的应用程序中都运行良好，但我们也给予了用户持久化每一个RDD的控制权。
> Finally, each instance of Spark on a cluster currently has its own separate memory space. In future work, we plan to investigate sharing RDDs across instances of Spark through a unified memory manager.
> 最后，集群上的每个 Spark 实例当前都有自己独立的内存空间。 在未来的工作中，我们计划研究通过统一的内存管理器在 Spark 实例之间共享 RDD。

Todo：实现了吗？
### 如何表达 RDD
#### RDD 的编程接口表达
比如，基于一个 HDFS 文件创建出来的的 RDD 中文件的每一个数据块就是一个分区，并且这个 RDD 知道每一个数据块存储在哪些机器上，同时，在这个 RDD 上进行 map 操作后的结果有相同的分区数，当计算元素的时候，将 map 函数应用到父亲 RDD 数据中的。我们在表三总结了这些接口:

| **操作接口** | **含义** |
| --- | --- |
| partitions() | 返回一个分区对象的列表 |
| preferredLocations(p) | List nodes where partition p can be accessed faster due to data locality |
| dependencies() | 返回一个依赖列表 |
| iterator(p, parentIters) | Compute the elements of partition p given iterators for its parent partitions |
| partitioner() | 返回这个RDD是hash还是range分区的元数据信息 |

#### RDD 依赖的表达
![image.png](https://cdn.nlark.com/yuque/0/2024/png/2847893/1709264545716-b4ffdda4-b14f-470a-b06f-f8b6d76b9042.png#averageHue=%23f3f2f2&clientId=u2fc4cad2-9317-4&from=paste&id=a9Ovz&originHeight=594&originWidth=904&originalType=url&ratio=1&rotation=0&showTitle=false&size=134371&status=done&style=none&taskId=u25609960-5960-4f5a-b4af-4422df6c5a4&title=)<br />窄依赖和宽依赖的例子。每一个方框表示一个 RDD，带有颜色的矩形表示分区

以下两个原因使的这种区别很有用

1. 窄依赖可以使得在集群中一个机器节点的执行流计算所有父亲的分区数据，比如，我们可以将每一个元素应用了 map 操作后紧接着应用 filter 操作，与此相反，宽依赖需要父亲 RDDs 的所有分区数据准备好并且利用类似于 MapReduce 的操作将数据在不同的节点之间进行重新洗牌和网络传输。
2. 窄依赖从一个失败节点中恢复是非常高效的，因为只需要重新计算相对应的父亲的分区数据就可以，而且这个重新计算是在不同的节点进行并行重计算的，与此相反，在一个含有宽依赖的血缘关系 RDDs 图中，一个节点的失败可能导致一些分区数据的丢失，但是我们需要重新计算父 RDD 的所有分区的数据。
### Job 任务调度 / Stage 的划分
当一个用户对某个 RDD 调用了 action 操作（比如 count 或者 save）的时候调度器会检查这个 RDD 的血缘关系图，然后根据这个血缘关系图构建一个含有 stages 的有向无环图（DAG），最后按照步骤执行这个 DAG 中的 stages。<br />每一个 stage 包含了尽可能多的带有窄依赖的 transformations 操作。这个 stage 的划分是根据需要 shuffle 操作的宽依赖或者任何可以切断对父亲 RDD 计算的某个操作（因为这些父亲 RDD 的分区已经计算过了）。然后调度器可以调度启动 tasks 来执行没有父亲 stage 的 stage（或者父亲 stage 已经计算好了的 stage），一直到计算完我们的最后的目标 RDD 。<br />![9a1ca367603942cde5c30e70396e8fa3.jpg](https://cdn.nlark.com/yuque/0/2024/jpeg/2847893/1710137013366-82bb8650-d2cb-4b00-baa4-84aa7e2332ba.jpeg#averageHue=%23ededed&clientId=u27b8588b-446b-4&from=ui&id=NjW3d&originHeight=580&originWidth=824&originalType=binary&ratio=2&rotation=0&showTitle=false&size=110516&status=done&style=none&taskId=u5690b44a-08c4-423e-bd67-3e0dddb3d14&title=)<br />每一个 stage 包含了尽可能多的带有窄依赖的 transformations 操作。<br />方框表示 RDDs ，带有颜色的方形表示分区，黑色的是表示这个分区的数据存储在内存中。<br />我们调度器在分配 tasks 的时候是采用延迟调度来达到数据本地性的目的（说白了，就是数据在哪里，计算就在哪里）。如果某个分区的数据在某个节点上的内存中，那么将这个分区的计算发送到这个机器节点中。如果某个 RDD 为它的某个分区提供了这个数据存储的位置节点，则将这个分区的计算发送到这个节点上。<br />对于宽依赖（比如 shuffle 依赖），我们将中间数据写入到节点的磁盘中以利于从错误中恢复，这个和 MapReduce 将 map 后的结果写入到磁盘中是很相似的。
# QA
## 对于分布式文件系统，如何判断数据与节点的远近？换句话说就是怎么判断计算任务该发给哪个节点？
todo: ...
## 如何解决数据倾斜？
除了手动指定分区方法外还有比较好的优化方案吗？
## 如何检测分区数据丢失？？
像 hdfs 那样每个块使用一个检验和？
## RDDs相对于DSM的粗粒度里的粗和细是指什么？
DSM （分布式内存）系统里面的粒度指的是每一个 byte ，每一个 byte 的更改都是需要全局同步的。<br />RDDs 里的粒度是指每一个 RDD & 分区 ，以 RDD & 分区 作为基本单位进行计算、恢复操作。
# 论文摘抄
## 第二节
### 2.1 RDD抽象
一个 RDD 是一个只读，被分区的数据集。<br />RDDs 并不要始终被具体化，一个 RDD 有足够的信息知道自己是从哪个数据集计算而来的（就是所谓的依赖血统），这是一个非常强大的属性：**事实上，一个程序不能引用一个不能从失败中重新构建的 RDD。**
> **in essence, a program cannot reference an RDD that it cannot reconstruct after a failure.**

最后，用户可以控制 RDDs 的两个方面：数据存储和分区。对于需要复用的 RDD，用户可以明确的选择一个数据存储策略（比如内存缓存）。他们也可以基于一个元素的 key 来为 RDD 所有的元素在机器节点间进行数据分区，这样非常利于数据分布优化，比如给两个数据集进行相同的 hash 分区，然后进行 join，可以提高 join 的性能。
### 2.3 RDD 模型的优势
| Aspect | RDDs | **Distribute shared memory** |
| --- | --- | --- |
| Reads | 粗粒度或者细粒度 | 细粒度 |
| Writes | 粗粒度 | 细粒度 |
| 数据一致性 | 不重要的（因为RDD是不可变的） | 取决于app 或者 runtime |
| 容错 | 利用 lineage 达到细粒度且低延迟的容错 | 需要应用checkpoints（就是需要写磁盘）并且需要程序回滚 |
| Straggler mitigation | Possible using backup<br />tasks | Difficult |
| 计算数据的位置 | Automatic based on data locality | 取决于app（runtime是以透明为目标的） |
| 内存不足时的行为 | 和已经存在的数据流处理系统一样，写磁盘 | Poor performance (swapping?) |

RDDs 只能通过粗粒度的转换被创建（或者被写），然而 DSM 允许对每一个内存位置进行读写，这个是 RDDs 和 DSM 最主要的区别。这样使都 RDDs在 应用中大量写数据受到了限制，但是可以使的容错变的更加高效。特别是，RDDs 不需要发生非常耗时的 checkpoint 操作，因为它可以根据 lineage 进行恢复数据。而且，只有丢掉了数据的分区才会需要重新计算，并不需要回滚整个程序，并且这些重新计算的任务是在多台机器上并行运算的。
> Furthermore, only the lost partitions of an RDD need to be recomputed upon failure, and they can be recomputed in parallel on different nodes, without having to roll back the whole program.<br />此外，故障时只需重新计算RDD丢失的分区，并且可以在不同节点上并行重新计算，而无需回滚整个程序。

RDDs 的第二个好处是：它不变的特性使的它可以和 MapReduce 一样来运行执行很慢任务的备份任务来达到缓解计算很慢的节点的问题。在 DSM 中，备份任务是很难实现的，因为原始任务和备份任务或同时更新访问同一个内存地址和接口。<br />最后，RDDs 比 DSM 多提供了两个好处。第一，在对 RDDs 进行大量写操作的过程中，我们可以根据数据的本地性来调度 task 以提高性能。第二，如果在 scan-base 的操作中，且这个时候内存不足以存储这个 RDDs，那么 RDDs 可以慢慢的从内存中清理掉。在内存中存储不下的分区数据会被写到磁盘中，且提供了和现有并行数据处理系统相同的性能保证。
