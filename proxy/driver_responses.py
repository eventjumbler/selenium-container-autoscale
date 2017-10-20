from sanic.response import json as json_resp
from sanic.response import text as text_resp


def new_driver_resp(session_id, error=False):
    if error:
        return _new_driver_resp_error(session_id)
    st = '''{
        "sessionId": "%(session_id)s",
        "state": null,
        "hCode": 1392544916,
        "value": {
            "moz:profile": "/tmp/rust_mozprofile.yF5RazbLPPcX",
            "rotatable": false,
            "timeouts": {
                "implicit": 0.0,
                "pageLoad": 300000.0,
                "script": 30000.0
            },
            "pageLoadStrategy": "normal",
            "platform": "ANY",
            "specificationLevel": 0.0,
            "moz:accessibilityChecks": false,
            "webdriver.remote.sessionid": "%(session_id)s",
            "acceptInsecureCerts": false,
            "browserVersion": "%(browser_version)s",
            "platformVersion": "4.4.62-hyper",
            "moz:processID": 65.0,
            "browserName": "firefox",
            "takesScreenshot": true,
            "javascriptEnabled": true,
            "platformName": "linux",
            "cssSelectorsEnabled": true
        },
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }''' % {
        'browser_version': '53.0.3',  # todo: will need to be updated
        'session_id': session_id,
    }
    return text_resp(st)


def _new_driver_resp_error(session_id):
    resp = {
        "value": {
            "stacktrace": "org.openqa.selenium.WebDriverException: Process unexpectedly closed with status: 1\nBuild info: version: '3.6.0', revision: '6fbf3ec767', time: '2017-09-27T16:15:40.131Z'\nSystem info: host: '1bab8fee6817', ip: '172.16.0.174', os.name: 'Linux', os.arch: 'amd64', os.version: '4.4.62-hyper', java.version: '1.8.0_131'\nDriver info: driver.version: unknown\nremote stacktrace: stack backtrace:\n   0:           0x4f388c - backtrace::backtrace::trace::h736111741fa0878e\n   1:           0x4f38c2 - backtrace::capture::Backtrace::new::h63b8a5c0787510c9\n   2:           0x442d88 - webdriver::error::WebDriverError::new::hea6d4dbf778b2b24\n   3:           0x44a8c3 - geckodriver::marionette::MarionetteHandler::create_connection::hf8b6061dba65cdd0\n   4:           0x42ac91 - <webdriver::server::Dispatcher<T, U>>::run::hba9181b5aacf8f04\n   5:           0x402c59 - std::sys_common::backtrace::__rust_begin_short_backtrace::h19de262639927233\n   6:           0x40c065 - std::panicking::try::do_call::h6c1659fc4d01af51\n   7:           0x5e38ec - panic_unwind::__rust_maybe_catch_panic\n                        at /checkout/src/libpanic_unwind/lib.rs:98\n   8:           0x420d32 - <F as alloc::boxed::FnBox<A>>::call_box::h953e5f59694972c5\n   9:           0x5dc00b - alloc::boxed::{{impl}}::call_once<(),()>\n                        at /checkout/src/liballoc/boxed.rs:661\n                         - std::sys_common::thread::start_thread\n                        at /checkout/src/libstd/sys_common/thread.rs:21\n                         - std::sys::imp::thread::{{impl}}::new::thread_start\n                        at /checkout/src/libstd/sys/unix/thread.rs:84\n\tat sun.reflect.NativeConstructorAccessorImpl.newInstance0(Native Method)\n\tat sun.reflect.NativeConstructorAccessorImpl.newInstance(NativeConstructorAccessorImpl.java:62)\n\tat sun.reflect.DelegatingConstructorAccessorImpl.newInstance(DelegatingConstructorAccessorImpl.java:45)\n\tat java.lang.reflect.Constructor.newInstance(Constructor.java:423)\n\tat org.openqa.selenium.remote.W3CHandshakeResponse.lambda$new$0(W3CHandshakeResponse.java:57)\n\tat org.openqa.selenium.remote.W3CHandshakeResponse.lambda$getResponseFunction$2(W3CHandshakeResponse.java:104)\n\tat org.openqa.selenium.remote.ProtocolHandshake.lambda$createSession$24(ProtocolHandshake.java:359)\n\tat java.util.stream.ReferencePipeline$3$1.accept(ReferencePipeline.java:193)\n\tat java.util.Spliterators$ArraySpliterator.tryAdvance(Spliterators.java:958)\n\tat java.util.stream.ReferencePipeline.forEachWithCancel(ReferencePipeline.java:126)\n\tat java.util.stream.AbstractPipeline.copyIntoWithCancel(AbstractPipeline.java:498)\n\tat java.util.stream.AbstractPipeline.copyInto(AbstractPipeline.java:485)\n\tat java.util.stream.AbstractPipeline.wrapAndCopyInto(AbstractPipeline.java:471)\n\tat java.util.stream.FindOps$FindOp.evaluateSequential(FindOps.java:152)\n\tat java.util.stream.AbstractPipeline.evaluate(AbstractPipeline.java:234)\n\tat java.util.stream.ReferencePipeline.findFirst(ReferencePipeline.java:464)\n\tat org.openqa.selenium.remote.ProtocolHandshake.createSession(ProtocolHandshake.java:362)\n\tat org.openqa.selenium.remote.server.ServicedSession$Factory.apply(ServicedSession.java:185)\n\tat org.openqa.selenium.remote.server.ActiveSessionFactory.lambda$createSession$16(ActiveSessionFactory.java:171)\n\tat java.util.Optional.map(Optional.java:215)\n\tat org.openqa.selenium.remote.server.ActiveSessionFactory.createSession(ActiveSessionFactory.java:171)\n\tat org.openqa.selenium.remote.server.commandhandler.BeginSession.execute(BeginSession.java:72)\n\tat org.openqa.selenium.remote.server.WebDriverServlet.lambda$handle$0(WebDriverServlet.java:232)\n\tat java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)\n\tat java.util.concurrent.FutureTask.run(FutureTask.java:266)\n\tat java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)\n\tat java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)\n\tat java.lang.Thread.run(Thread.java:748)\n",
            "stackTrace": [{
                "fileName": "ThreadPoolExecutor.java",
                "methodName": "run",
                "className": "java.util.concurrent.ThreadPoolExecutor$Worker",
                "lineNumber": 624
            }, {
                "fileName": "Thread.java",
                "methodName": "run",
                "className": "java.lang.Thread",
                "lineNumber": 748
            }],
            "message": "Exception when trying to launch driver",
            "error": "unknown error"
        },
        "status": 13
    }
    # original "message" value: "Process unexpectedly closed with status: 1\nBuild info: version: '3.6.0', revision: '6fbf3ec767', time: '2017-09-27T16:15:40.131Z'\nSystem info: host: '1bab8fee6817', ip: '172.16.0.174', os.name: 'Linux', os.arch: 'amd64', os.version: '4.4.62-hyper', java.version: '1.8.0_131'\nDriver info: driver.version: unknown\nremote stacktrace: stack backtrace:\n   0:           0x4f388c - backtrace::backtrace::trace::h736111741fa0878e\n   1:           0x4f38c2 - backtrace::capture::Backtrace::new::h63b8a5c0787510c9\n   2:           0x442d88 - webdriver::error::WebDriverError::new::hea6d4dbf778b2b24\n   3:           0x44a8c3 - geckodriver::marionette::MarionetteHandler::create_connection::hf8b6061dba65cdd0\n   4:           0x42ac91 - <webdriver::server::Dispatcher<T, U>>::run::hba9181b5aacf8f04\n   5:           0x402c59 - std::sys_common::backtrace::__rust_begin_short_backtrace::h19de262639927233\n   6:           0x40c065 - std::panicking::try::do_call::h6c1659fc4d01af51\n   7:           0x5e38ec - panic_unwind::__rust_maybe_catch_panic\n                        at /checkout/src/libpanic_unwind/lib.rs:98\n   8:           0x420d32 - <F as alloc::boxed::FnBox<A>>::call_box::h953e5f59694972c5\n   9:           0x5dc00b - alloc::boxed::{{impl}}::call_once<(),()>\n                        at /checkout/src/liballoc/boxed.rs:661\n                         - std::sys_common::thread::start_thread\n                        at /checkout/src/libstd/sys_common/thread.rs:21\n                         - std::sys::imp::thread::{{impl}}::new::thread_start\n                        at /checkout/src/libstd/sys/unix/thread.rs:84"
    return json_resp(resp, 500)


'''
another version: 

	"value": {
		"sessionId": "ab671230-421b-44c8-934c-3c6ae314fa52",
		"capabilities": {
			"moz:profile": "/tmp/rust_mozprofile.NlwihK1sBXV0",
			"rotatable": false,
			"timeouts": {
				"implicit": 0,
				"pageLoad": 300000,
				"script": 30000
			},
			"pageLoadStrategy": "normal",
			"moz:headless": false,
			"specificationLevel": 0,
			"moz:accessibilityChecks": false,
			"acceptInsecureCerts": true,
			"browserVersion": "56.0",
			"platformVersion": "4.4.62-hyper",
			"moz:processID": 75,
			"browserName": "firefox",
			"platformName": "linux"
		}
	}
}

'''


def page_get_response(session_id, state='success'):  # for state strings see: https://github.com/SeleniumHQ/selenium/blob/ceaf3da79542024becdda5953059dfbb96fb3a90/third_party/closure/goog/net/eventtype.js
    return text_resp('''{
        "sessionId": "%(session_id)s",
        "state": "success",
        "hCode": 1105373391,
        "value": null,
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }''' % {'session_id': session_id}
    )


def quit_response(session_id, error=False):
    resp = {
        "sessionId": session_id,
        "state": "error" if error else "success",
        "hCode": 225874638,
        "value": None,
        "class": "org.openqa.selenium.remote.Response",
        "status": 0
    }
    status = 500 if error else 200
    if error:
        resp['message'] = ''
    return json_resp(resp, status=status)