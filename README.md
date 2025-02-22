# Multilayer caching

Multilayered here means that one cache layer may depend on another, which in turn may depend on another...
Also being capable of forming not only chains, but trees of dependent caches.
Value retrievals update local cache of all downstream layers.

## Our example

For example, say, we have a files stored on an S3 bucket which we want to cache locally,
and also cache the parsed data structures derived from these files.
It gives us a 2-layer cache structure with Bucket as data source.

```
Bucket  
 ├── File Cache  
 │   ├── Parsed File Cache  
```

Say you want a parsed value. So you are concerned with **Parsed File Cache**.

With both local caches being empty, let's describe what would happen for the first time value retrieval.

Since **Parsed File Cache** would *not* find it in local cache, then it would try to retrieve it from its dependant - **File Cache**.
**File Cache** would also *not* find a transformable value in its local cache, and to the dependant it goes - **Bucket**.

**Bucket** may or may *not* have a value.
If it doesn't - no local cache updates happen, and the result of retrieval from **Parsed File Cache** is a value standing for *Key not found*. But if it does, **File Cache** uses the retrieved value from **Bucket** and stores a transformed value in local cache, and **Parsed File Cache** does the same.

When values found in local caches, the found values pop out as soon as found, and caches do not contact its dependants.

It's a simple recursive algorithm.

### More elaborate cache structures

For the sake of brevity, we investigate this minimal example, but arbitrary nested tree cache structures are possible nonetheless:

```
Bucket  
 ├── File Cache  
 │   ├── Parsed File Cache  
 │   │   ├── Further Parsed File Cache  
 │   ├── Another Parsed File Cache  
```

## Implementation

### Common problems

Implementing such caching still may be a challenge. The implementation may suffer from:

- spagetti
  (Having recursive nature, but of finite nesting. For your purposes
  you may have started it with one layer, but after adding a layer or two more
  the code started looking from afar like)
```
@@@@ outer layer get
  @@@@ middle layer get
    @@@@ inner layer get
  @@@@
@@@@
```

- imposing too tight contracts and controlling inner cache

- mixing-in more logic than necessary (due to lack of formalization and restrictions)

### Approach

In implemenation the concern is too provide as flexible way to construct caches as possible.
It's achieved by imposing only the essential to the problem constraints
(which at the same time provide freedom by enforcing similarity of different layers)

### Python implementation

```python
# Represents value type a cache returns
T = TypeVar("T")
# Represent [K]ey used for retrieving from local cache or source
K = TypeVar("K")
# Represents unique (in "is" operation) [D]efault value that should be returned on not found key
D = TypeVar("D")


def cache_layer(
    # A way to get a cache key
    get_cache_key: Callable[[], K],
    # A way to use the key from local cache to get a value
    get_cache_value: Callable[[K, D], T],
    # A way to update local cache with the key and value
    set_cache_value: Callable[[K, T], None],
    # A way to get value from the dependant source with the key
    on_cache_miss_source: Callable[[K, D], T],
    # A way to get a unique value the local cache and dependant source would return when the key not found
    get_default: Callable[[], D],
    # A way to get an identifier for a cache layer
    get_identifier: Callable[[], Any],
    # Handler of generated events, for example for testing and logging
    inspect: Callable[[CacheLayerInspect], None] = lambda _: None,
) -> T:
    ...
```

For nesting of layers L(0..N) to be possible (where L_0 is the most inner layer and L_N is the most outer layer)

For T(0..N) must be such as there must exist a one-way transformation (morfism) T_0 -> T_N.
Simply, there must be a way to reduce a **value** passing from *inner to outer* layer.
For example, it works with bytes -> decoded bytes -> parsed json

For K(0..N) must be such as there must exist a one-way transformation (morfism) K_N -> K_0.
Simply, there must be a way to reduce a **key** passing from *outer to inner* layer.

