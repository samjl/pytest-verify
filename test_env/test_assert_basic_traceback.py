from pytest import log


def test_assert_traceback():
    log.high_level_step("Test the pytest-verify plugin")
    log.high_level_step("Standard assert traceback test")

    def stack_l3_assert(k):
        print "Finally verifying x, j, k"
        assert k is True, "test k is True (assert-fail)"

    def stack_l2_assert(j):
        print "In stack_l2 function"
        print "about to call stack_l3..."
        stack_l3_assert(j)

    def stack_l1_assert(i):
        stack_l2_assert(i)

    x = False
    stack_l1_assert(x)

    log.detail_step("End of test_assert_traceback")  # Should not execute
