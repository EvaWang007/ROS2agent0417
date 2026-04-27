## Blacklist机制
> 原理
`blacklist` 一般叫 **黑名单**。

它的核心含义是：

**把某些“不允许通过”的对象列出来，命中后就拒绝。**

---

最直观的理解

你可以把它理解成一个“禁止名单”。

比如有一个列表：

```text
["topic_a", "topic_b", "private_node"]
```

意思就是：

* 如果请求里出现 `topic_a`
* 或者出现 `topic_b`
* 或者出现 `private_node`

那系统就不允许访问、执行或返回这些内容。

---

> 在程序里它通常起什么作用

1. 限制访问

比如：

* 不允许访问某些文件
* 不允许调用某些接口
* 不允许读取某些 ROS topic / node

2. 做安全控制

比如：

* 防止用户操作敏感资源
* 防止 agent 调用高风险工具
* 防止访问私有数据

3. 过滤输出

比如：

* 返回结果里如果包含黑名单项，就隐藏掉
* 工具调用前如果参数命中黑名单，就直接拒绝

---

> 一个简单例子

假设你有个工具：

```python
def read_topic(topic_name):
    ...
```

你希望某些 topic 不允许读取：

```python
blacklist = ["/camera/raw", "/private/debug"]
```

那逻辑可以是：

```python
if topic_name in blacklist:
    raise ValueError("不允许访问该 topic")
```

意思就是：

* 普通 topic 可以读
* 黑名单里的 topic 不可以读

---

> 在 ROSA 里的 blacklist 是什么作用

在 ROSA 这种 agent 项目里，`blacklist` 的作用就是：

> **限制 agent 不要访问某些敏感 ROS 资源。**

比如你可以把一些：

* 私有 topic
* 敏感 node
* 不希望暴露的 service

放进 blacklist。

这样 agent 虽然有工具能力，但一旦想访问这些对象，就会被拦住。

所以它本质上是一种**工具层安全限制**。

---


> **blacklist 就是黑名单，用来列出禁止访问、禁止调用、禁止通过的对象；命中黑名单后，系统会拒绝该操作。**

