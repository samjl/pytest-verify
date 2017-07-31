from pytest import log, verify, get_saved_results


def test_basic_traceback():
    log.high_level_step("Basic traceback test")

    fail_condition = lambda x: x is True
    verify("Check something is true (passes)", fail_condition, True)
    verify("Check something is true (fails)", fail_condition, False,
           raise_assertion=False)
    # Retrieve the saved results and traceback info for any failed
    # verifications.
    saved_results, saved_tracebacks = get_saved_results()
    for saved_tb in saved_tracebacks:
        print "Traceback:raised: {}".format(saved_tb["raised"])
        print "Traceback:complete:"
        print saved_tb["complete"]
        for line in saved_tb["complete"]:
            log.step(line)  # same output as "print line"

    log.detail_step("End of test")
