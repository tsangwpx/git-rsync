def cached_result(underlying):
    """
    Cache the result of the underlying function so that invocations always return the same result
    :param underlying:
    :return:
    """

    def func():
        if not func.called:
            func.result = underlying()
            func.called = True

        return func.result

    func.called = False

    return func
