"""Small authored Python maintenance tasks; oracles never enter the agent workspace."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    instruction: str
    source: str
    solution: str
    cases: tuple
    constraint: str = ""


TASKS = [
    Task("sum", "bug", "Fix total(values) to sum all values, including an empty list.",
         "def total(values):\n    return sum(values[1:])\n",
         "def total(values):\n    return sum(values)\n",
         (([1, 2, 3], 6), ([], 0), ([-4, 2], -2))),
    Task("median", "bug", "Fix median(values) for odd and even nonempty numeric lists without mutating input.",
         "def median(values):\n    values.sort()\n    return values[len(values) // 2]\n",
         "def median(values):\n    x = sorted(values)\n    n = len(x)\n    return x[n//2] if n%2 else (x[n//2-1]+x[n//2])/2\n",
         (([3, 1, 2], 2), ([4, 1, 3, 2], 2.5), ([7], 7)), "no_mutation"),
    Task("unique", "bug", "Fix unique(values) to remove duplicates while preserving first-occurrence order for hashable values.",
         "def unique(values):\n    return sorted(set(values))\n",
         "def unique(values):\n    return list(dict.fromkeys(values))\n",
         (([3, 1, 3, 2], [3, 1, 2]), ([], []), ([2, 2], [2]))),
    Task("factorial", "bug", "Fix factorial(n) for nonnegative integers; negative input must raise ValueError.",
         "def factorial(n):\n    result = 1\n    for i in range(1, n):\n        result *= i\n    return result\n",
         "def factorial(n):\n    if n < 0: raise ValueError('negative')\n    result = 1\n    for i in range(1, n+1): result *= i\n    return result\n",
         ((0, 1), (5, 120), (-1, {"raises": "ValueError"}))),
    Task("palindrome", "bug", "Fix palindrome(text): ignore case and non-alphanumeric characters; empty normalized text is a palindrome.",
         "def palindrome(text):\n    return text == text[::-1]\n",
         "def palindrome(text):\n    x = ''.join(c.lower() for c in text if c.isalnum())\n    return x == x[::-1]\n",
         (("A man, a plan, a canal: Panama", True), ("hello", False), ("!?", True))),
    Task("flatten", "bug", "Fix flatten(rows) to flatten exactly one level, preserving order and empty rows.",
         "def flatten(rows):\n    return [row[0] for row in rows]\n",
         "def flatten(rows):\n    return [x for row in rows for x in row]\n",
         (([[1, 2], [], [3]], [1, 2, 3]), ([], []), ([[[1]]], [[1]]))),
    Task("counts", "bug", "Fix counts(values) to return occurrence counts of hashable values.",
         "def counts(values):\n    return {x: 1 for x in values}\n",
         "def counts(values):\n    result = {}\n    for x in values: result[x] = result.get(x, 0) + 1\n    return result\n",
         ((["a", "b", "a"], {"a": 2, "b": 1}), ([], {}), ([1, 1, 1], {1: 3}))),
    Task("slug", "bug", "Fix slug(text): lowercase ASCII letters/digits, replace runs of all other characters with one hyphen and strip edge hyphens.",
         "def slug(text):\n    return text.lower().replace(' ', '-')\n",
         "import re\ndef slug(text):\n    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')\n",
         (("  Hello, World! ", "hello-world"), ("a___b", "a-b"), ("!!!", ""))),
    Task("chunks", "bug", "Fix chunks(spec), where spec is (values, size), returning consecutive chunks including remainder; nonpositive size raises ValueError.",
         "def chunks(spec):\n    values, size = spec\n    return [values[i:i+size] for i in range(0, len(values)-size, size)]\n",
         "def chunks(spec):\n    values, size = spec\n    if size <= 0: raise ValueError('size')\n    return [values[i:i+size] for i in range(0, len(values), size)]\n",
         ((([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]), (([], 2), []), (([1], 0), {"raises": "ValueError"}))),
    Task("clamp", "bug", "Fix clamp(spec), where spec is (value, lower, upper). Clamp inclusive bounds; lower > upper raises ValueError.",
         "def clamp(spec):\n    value, low, high = spec\n    return min(low, max(high, value))\n",
         "def clamp(spec):\n    value, low, high = spec\n    if low > high: raise ValueError('bounds')\n    return max(low, min(high, value))\n",
         (((5, 0, 10), 5), ((-2, 0, 10), 0), ((20, 0, 10), 10), ((1, 4, 2), {"raises": "ValueError"}))),
    Task("binary_search", "bug", "Fix binary_search(spec), where spec is (sorted_values, target), to return any matching index or -1, including empty lists.",
         "def binary_search(spec):\n    values, target = spec\n    lo, hi = 0, len(values)-1\n    while lo < hi:\n        mid = (lo+hi)//2\n        if values[mid] == target: return mid\n        if values[mid] < target: lo = mid+1\n        else: hi = mid-1\n    return -1\n",
         "def binary_search(spec):\n    values, target = spec\n    lo, hi = 0, len(values)-1\n    while lo <= hi:\n        mid = (lo+hi)//2\n        if values[mid] == target: return mid\n        if values[mid] < target: lo = mid+1\n        else: hi = mid-1\n    return -1\n",
         ((([1, 3, 5], 5), 2), (([2], 2), 0), (([], 1), -1), (([1, 3], 2), -1))),
    Task("is_prime", "bug", "Fix is_prime(n) for integer inputs, including numbers below 2 and perfect squares.",
         "def is_prime(n):\n    return all(n % i for i in range(2, int(n**0.5)))\n",
         "def is_prime(n):\n    return n >= 2 and all(n % i for i in range(2, __import__('math').isqrt(n)+1))\n",
         ((-4, False), (1, False), (2, True), (9, False), (17, True))),
    Task("running_total", "feature", "Implement running_total(values), returning cumulative sums in input order.",
         "def running_total(values):\n    raise NotImplementedError\n",
         "def running_total(values):\n    result, total = [], 0\n    for x in values:\n        total += x\n        result.append(total)\n    return result\n",
         (([1, 2, -1], [1, 3, 2]), ([], []), ([0], [0]))),
    Task("invert", "feature", "Implement invert(mapping), grouping original keys by value in insertion order into lists.",
         "def invert(mapping):\n    raise NotImplementedError\n",
         "def invert(mapping):\n    result = {}\n    for k,v in mapping.items(): result.setdefault(v, []).append(k)\n    return result\n",
         (({"a": 1, "b": 1, "c": 2}, {1: ["a", "b"], 2: ["c"]}), ({}, {}))),
    Task("rotate", "feature", "Implement rotate(spec) for (values, k): rotate right by k; negative k rotates left; empty input returns empty list.",
         "def rotate(spec):\n    raise NotImplementedError\n",
         "def rotate(spec):\n    values, k = spec\n    if not values: return []\n    k %= len(values)\n    return values[-k:] + values[:-k] if k else values[:]\n",
         ((([1, 2, 3], 1), [3, 1, 2]), (([1, 2, 3], -1), [2, 3, 1]), (([], 4), []), (([1, 2], 4), [1, 2]))),
    Task("balanced", "feature", "Implement balanced(text) for properly nested (), [], {}; ignore all other characters.",
         "def balanced(text):\n    raise NotImplementedError\n",
         "def balanced(text):\n    stack = []\n    pairs = {')':'(', ']':'[', '}':'{'}\n    for c in text:\n        if c in '([{': stack.append(c)\n        elif c in pairs:\n            if not stack or stack.pop() != pairs[c]: return False\n    return not stack\n",
         (("a{b[c](d)}", True), ("([)]", False), ("(", False), ("", True))),
    Task("merge_intervals", "feature", "Implement merge_intervals(intervals): merge overlapping or touching [start,end] intervals, sort output and do not mutate input.",
         "def merge_intervals(intervals):\n    raise NotImplementedError\n",
         "def merge_intervals(intervals):\n    result=[]\n    for a,b in sorted(intervals):\n        if result and a <= result[-1][1]: result[-1][1] = max(result[-1][1],b)\n        else: result.append([a,b])\n    return result\n",
         (([[5, 7], [1, 3], [3, 6]], [[1, 7]]), ([], []), ([[1, 2], [4, 5]], [[1, 2], [4, 5]])), "no_mutation"),
    Task("transpose", "feature", "Implement transpose(rows) returning a list of column lists. Empty rows -> []; ragged input raises ValueError.",
         "def transpose(rows):\n    raise NotImplementedError\n",
         "def transpose(rows):\n    if not rows: return []\n    if any(len(r) != len(rows[0]) for r in rows): raise ValueError('ragged')\n    return [list(col) for col in zip(*rows)]\n",
         (([[1, 2], [3, 4]], [[1, 3], [2, 4]]), ([], []), ([[1], [2, 3]], {"raises": "ValueError"}))),
    Task("refactor_sum", "refactor", "Refactor sum_squares(values) to contain no for/while statements, preserving behavior. Comprehensions/generators are allowed.",
         "def sum_squares(values):\n    total = 0\n    for value in values:\n        total += value * value\n    return total\n",
         "def sum_squares(values):\n    return sum(x*x for x in values)\n",
         (([1, -2, 3], 14), ([], 0), ([4], 16)), "no_loops"),
    Task("refactor_join", "refactor", "Refactor csv_line(values) to use str.join instead of a for/while statement, preserving comma separation and string conversion.",
         "def csv_line(values):\n    result = ''\n    for value in values:\n        if result: result += ','\n        result += str(value)\n    return result\n",
         "def csv_line(values):\n    return ','.join(str(x) for x in values)\n",
         (([1, 2, 3], "1,2,3"), ([], ""), (["a", "b"], "a,b")), "join"),
]

PAIRED_IDS = ["median", "binary_search", "balanced", "merge_intervals", "refactor_sum"]
