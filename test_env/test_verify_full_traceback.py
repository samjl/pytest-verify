from pytest import log, verify


def test_full_traceback():
    log.high_level_step("Test the pytest-verify plugin")
    log.high_level_step("Full traceback test")

    log.detail_step("Ensure there is no traceback for passed verifications")
    x = True
    verify(x is True, "Check x is true (passes)")

    log.detail_step("Ensure default behaviour is short trace back")
    x = False
    verify(x is True, "Check x is true (fails - call line tb)",
           raise_assertion=False)

    log.detail_step("Test no change when full_method_trace is set to False")
    x = False
    verify(x is True, "Check x is true (fails - call line tb)",
           raise_assertion=False, full_method_trace=False)

    log.detail_step("Test full function traceback is printed when "
                    "full_method_trace is set to True")
    x = False
    verify(x is True, "Check x is true (fails - full func tb)",
           raise_assertion=False, full_method_trace=True)

    log.detail_step("Test a function call as fail condition (fails)")

    def is_it_true(it):
        return it is True
    y = False
    verify(is_it_true(y), "test y is True (fail condition in function)",
           raise_assertion=False, full_method_trace=True)

    log.detail_step("Check traceback to call to verify over multiple stack "
                    "levels")

    def stack_l3(k):
        print "Finally verifying x, j, k"
        verify(k is True, "test k is True (fail)", raise_assertion=False,
               full_method_trace=True)

    def stack_l2(j):
        print "In stack_l2 function"
        print "about to call stack_l3..."
        stack_l3(j)

    def stack_l1(i):
        stack_l2(i)

    x = False
    stack_l1(x)

    log.detail_step("Test traceback depth past test function (into pytest "
                    "source)")
    verify(x is True, "Check x is true (fail)", raise_assertion=False,
           full_method_trace=True, stop_at_test=False)

    log.detail_step("End of test_full_traceback")
