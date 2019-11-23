import logging
import os
import time
import win32event

from win32com.client import *
from win32com.client.connect import *

logger = logging.getLogger(__name__)


class CanoeSync:
    """Wrapper class for CANoe Application object"""
    Started = False
    Stopped = False
    ConfigPath = ""
    TIMEOUT = 200
    stopMsgLoop = win32event.CreateEvent(None, 0, 0, None)

    def __init__(self):
        self.app = DispatchEx('CANoe.Application')
        self.app.Configuration.Modified = False
        version = '{}.{}.{}'.format(self.app.Version.major, self.app.Version.minor, self.app.Version.Build)
        logger.info('Loaded CANoe version {}'.format(version))
        self.Measurement = self.app.Measurement
        self.CompileResult = self.app.CAPL.CompileResult
        self.Running = lambda: self.Measurement.Running
        self.WaitForStart = lambda: DoEventsUntil(lambda: CanoeSync.Started)
        self.WaitForStartWithLimitedAttempts = lambda: DoEventsUntilWithLimitedAttempts(lambda: CanoeSync.Started, 20)
        self.WaitForStop = lambda: DoEventsUntil(lambda: CanoeSync.Stopped)
        WithEvents(self.app.Measurement, CanoeMeasurementEvents)

    def MessagePump(self):
        waitables = [CanoeSync.stopMsgLoop]

        while 1:
            rc = win32event.MsgWaitForMultipleObjects(
                waitables,
                0,  # Wait for all = false, so it waits for anyone
                CanoeSync.TIMEOUT,  # (or win32event.INFINITE)
                win32event.QS_ALLEVENTS)  # Accepts all input

            # You can call a function here, if it doesn't take too long. It will
            # be executed at least every 1000ms -- possibly a lot more often,
            # depending on the number of Windows messages received.

            if rc == win32event.WAIT_OBJECT_0:
                # Our first event listed, the StopEvent, was triggered, so we must exit
                # CanoeSync.Started = True
                # CanoeSync.Stopped = False
                # print("< measurement started >")
                return True
            elif rc == win32event.WAIT_OBJECT_0 + len(waitables):
                # A windows message is waiting - take care of it. (Don't ask me
                # why a WAIT_OBJECT_MSG isn't defined < WAIT_OBJECT_0...!).
                # This message-serving MUST be done for COM, DDE, and other
                # Windowsy things to work properly!
                if pythoncom.PumpWaitingMessages():
                    return False  # we received a wm_quit message
            elif rc == win32event.WAIT_TIMEOUT:
                # Our timeout has elapsed.
                # Do some work here (e.g, poll something you can't thread)
                # or just feel good to be alive.
                pass
            else:
                raise RuntimeError("unexpected win32wait return value")

    def SleepWithMessagePump(self, time):
        waitables = [CanoeSync.stopMsgLoop]
        totalTime = 0

        while 1:
            rc = win32event.MsgWaitForMultipleObjects(
                waitables,
                0,  # Wait for all = false, so it waits for anyone
                CanoeSync.TIMEOUT,  # (or win32event.INFINITE)
                win32event.QS_ALLEVENTS)  # Accepts all input

            # You can call a function here, if it doesn't take too long. It will
            # be executed at least every 1000ms -- possibly a lot more often,
            # depending on the number of Windows messages received.

            if rc == win32event.WAIT_OBJECT_0:
                # Our first event listed, the StopEvent, was triggered, so we must exit
                # CanoeSync.Started = True
                # CanoeSync.Stopped = False
                # print("< measurement started >")
                return True
            elif rc == win32event.WAIT_OBJECT_0 + len(waitables):
                # A windows message is waiting - take care of it. (Don't ask me
                # why a WAIT_OBJECT_MSG isn't defined < WAIT_OBJECT_0...!).
                # This message-serving MUST be done for COM, DDE, and other
                # Windowsy things to work properly!
                if pythoncom.PumpWaitingMessages():
                    return False  # we received a wm_quit message
            elif rc == win32event.WAIT_TIMEOUT:
                # Our timeout has elapsed.
                # Do some work here (e.g, poll something you can't thread)
                # or just feel good to be alive.
                if (totalTime > time):
                    return False

                totalTime = totalTime + CanoeSync.TIMEOUT

            else:
                raise RuntimeError("unexpected win32wait return value")

    def Load(self, cfgPath):
        # current dir must point to the script file
        cfg = os.path.join(os.curdir, cfgPath)
        cfg = os.path.abspath(cfg)
        logger.info('Opening: {}'.format(cfg))
        self.ConfigPath = os.path.dirname(cfg)
        self.Configuration = self.app.Configuration
        self.app.Open(cfg)

    def Start(self):
        if not self.Running():
            self.Measurement.Start()
            self.WaitForStart()

    def StartForMsgPump(self):
        if not self.Running():
            self.Measurement.Start()
            # self.WaitForStart()

    def StartWithTimeout(self):
        if not self.Running():
            self.Measurement.Start()
            self.WaitForStartWithLimitedAttempts()

    def Compile(self):
        if not self.Running():
            self.app.CAPL.Compile()
            time.sleep(2)

            return self.CompileResult.result

    def LatestCompileResult(self):
        if not self.Running():
            return self.CompileResult.result

    def CheckRunning(self):
        return self.Started

    def Stop(self):
        if self.Running():
            self.Measurement.Stop()
            self.WaitForStop()

    def Quit(self):
        self.Stop()
        self.app.Quit()


class CanoeMeasurementEvents(object):
    """Handler for CANoe measurement events"""

    def OnStart(self):
        CanoeSync.Started = True
        CanoeSync.Stopped = False
        win32event.SetEvent(CanoeSync.stopMsgLoop)
        logger.info("< measurement started >")

    def OnStop(self):
        CanoeSync.Started = False
        CanoeSync.Stopped = True
        win32event.SetEvent(CanoeSync.stopMsgLoop)
        logger.info("< measurement stopped >")


def DoEvents():
    pythoncom.PumpWaitingMessages()
    time.sleep(.1)


def DoEventsUntil(cond):
    while not cond():
        DoEvents()


def DoEventsUntilWithLimitedAttempts(cond, noOfAttempts):
    i = 0
    while ((not cond()) and (i < noOfAttempts)):
        DoEvents()
        i += 1
