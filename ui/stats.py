"""Request statistics"""


def print_stats(req):
    st = req.stats()
    print("=" * 40)
    print(f"  Total requests: {st['total']}")
    print(f"  Errors:   {st['errors']}")
    print(f"  Total time:   {st['time']:.2f}s")
    if st["total"]:
        print(f"  Average time: {st['time'] / st['total']:.3f}s")
    print("=" * 40)