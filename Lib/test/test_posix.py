"Test posix functions"

from test import support
from test.support.script_helper import assert_python_ok

# Skip these tests if there is no posix module.
posix = support.import_module('posix')

import errno
import sys
import signal
import time
import os
import platform
import pwd
import stat
import tempfile
import unittest
import warnings
import textwrap

_DUMMY_SYMLINK = os.path.join(tempfile.gettempdir(),
                              support.TESTFN + '-dummy-symlink')

requires_32b = unittest.skipUnless(sys.maxsize < 2**32,
        'test is only meaningful on 32-bit builds')

def _supports_sched():
    if not hasattr(posix, 'sched_getscheduler'):
        return False
    try:
        posix.sched_getscheduler(0)
    except OSError as e:
        if e.errno == errno.ENOSYS:
            return False
    return True

requires_sched = unittest.skipUnless(_supports_sched(), 'requires POSIX scheduler API')

class PosixTester(unittest.TestCase):

    def setUp(self):
        # create empty file
        fp = open(support.TESTFN, 'w+')
        fp.close()
        self.teardown_files = [ support.TESTFN ]
        self._warnings_manager = support.check_warnings()
        self._warnings_manager.__enter__()
        warnings.filterwarnings('ignore', '.* potential security risk .*',
                                RuntimeWarning)

    def tearDown(self):
        for teardown_file in self.teardown_files:
            support.unlink(teardown_file)
        self._warnings_manager.__exit__(None, None, None)

    def testNoArgFunctions(self):
        # test posix functions which take no arguments and have
        # no side-effects which we need to cleanup (e.g., fork, wait, abort)
        NO_ARG_FUNCTIONS = [ "ctermid", "getcwd", "getcwdb", "uname",
                             "times", "getloadavg",
                             "getegid", "geteuid", "getgid", "getgroups",
                             "getpid", "getpgrp", "getppid", "getuid", "sync",
                           ]

        for name in NO_ARG_FUNCTIONS:
            posix_func = getattr(posix, name, None)
            if posix_func is not None:
                posix_func()
                self.assertRaises(TypeError, posix_func, 1)

    @unittest.skipUnless(hasattr(posix, 'getresuid'),
                         'test needs posix.getresuid()')
    def test_getresuid(self):
        user_ids = posix.getresuid()
        self.assertEqual(len(user_ids), 3)
        for val in user_ids:
            self.assertGreaterEqual(val, 0)

    @unittest.skipUnless(hasattr(posix, 'getresgid'),
                         'test needs posix.getresgid()')
    def test_getresgid(self):
        group_ids = posix.getresgid()
        self.assertEqual(len(group_ids), 3)
        for val in group_ids:
            self.assertGreaterEqual(val, 0)

    @unittest.skipUnless(hasattr(posix, 'setresuid'),
                         'test needs posix.setresuid()')
    def test_setresuid(self):
        current_user_ids = posix.getresuid()
        self.assertIsNone(posix.setresuid(*current_user_ids))
        # -1 means don't change that value.
        self.assertIsNone(posix.setresuid(-1, -1, -1))

    @unittest.skipUnless(hasattr(posix, 'setresuid'),
                         'test needs posix.setresuid()')
    def test_setresuid_exception(self):
        # Don't do this test if someone is silly enough to run us as root.
        current_user_ids = posix.getresuid()
        if 0 not in current_user_ids:
            new_user_ids = (current_user_ids[0]+1, -1, -1)
            self.assertRaises(OSError, posix.setresuid, *new_user_ids)

    @unittest.skipUnless(hasattr(posix, 'setresgid'),
                         'test needs posix.setresgid()')
    def test_setresgid(self):
        current_group_ids = posix.getresgid()
        self.assertIsNone(posix.setresgid(*current_group_ids))
        # -1 means don't change that value.
        self.assertIsNone(posix.setresgid(-1, -1, -1))

    @unittest.skipUnless(hasattr(posix, 'setresgid'),
                         'test needs posix.setresgid()')
    def test_setresgid_exception(self):
        # Don't do this test if someone is silly enough to run us as root.
        current_group_ids = posix.getresgid()
        if 0 not in current_group_ids:
            new_group_ids = (current_group_ids[0]+1, -1, -1)
            self.assertRaises(OSError, posix.setresgid, *new_group_ids)

    @unittest.skipUnless(hasattr(posix, 'initgroups'),
                         "test needs os.initgroups()")
    def test_initgroups(self):
        # It takes a string and an integer; check that it raises a TypeError
        # for other argument lists.
        self.assertRaises(TypeError, posix.initgroups)
        self.assertRaises(TypeError, posix.initgroups, None)
        self.assertRaises(TypeError, posix.initgroups, 3, "foo")
        self.assertRaises(TypeError, posix.initgroups, "foo", 3, object())

        # If a non-privileged user invokes it, it should fail with OSError
        # EPERM.
        if os.getuid() != 0:
            try:
                name = pwd.getpwuid(posix.getuid()).pw_name
            except KeyError:
                # the current UID may not have a pwd entry
                raise unittest.SkipTest("need a pwd entry")
            try:
                posix.initgroups(name, 13)
            except OSError as e:
                self.assertEqual(e.errno, errno.EPERM)
            else:
                self.fail("Expected OSError to be raised by initgroups")

    @unittest.skipUnless(hasattr(posix, 'statvfs'),
                         'test needs posix.statvfs()')
    def test_statvfs(self):
        self.assertTrue(posix.statvfs(os.curdir))

    @unittest.skipUnless(hasattr(posix, 'fstatvfs'),
                         'test needs posix.fstatvfs()')
    def test_fstatvfs(self):
        fp = open(support.TESTFN)
        try:
            self.assertTrue(posix.fstatvfs(fp.fileno()))
            self.assertTrue(posix.statvfs(fp.fileno()))
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'ftruncate'),
                         'test needs posix.ftruncate()')
    def test_ftruncate(self):
        fp = open(support.TESTFN, 'w+')
        try:
            # we need to have some data to truncate
            fp.write('test')
            fp.flush()
            posix.ftruncate(fp.fileno(), 0)
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'truncate'), "test needs posix.truncate()")
    def test_truncate(self):
        with open(support.TESTFN, 'w') as fp:
            fp.write('test')
            fp.flush()
        posix.truncate(support.TESTFN, 0)

    @unittest.skipUnless(getattr(os, 'execve', None) in os.supports_fd, "test needs execve() to support the fd parameter")
    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    @unittest.skipUnless(hasattr(os, 'waitpid'), "test needs os.waitpid()")
    def test_fexecve(self):
        fp = os.open(sys.executable, os.O_RDONLY)
        try:
            pid = os.fork()
            if pid == 0:
                os.chdir(os.path.split(sys.executable)[0])
                posix.execve(fp, [sys.executable, '-c', 'pass'], os.environ)
            else:
                self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        finally:
            os.close(fp)


    @unittest.skipUnless(hasattr(posix, 'waitid'), "test needs posix.waitid()")
    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    def test_waitid(self):
        pid = os.fork()
        if pid == 0:
            os.chdir(os.path.split(sys.executable)[0])
            posix.execve(sys.executable, [sys.executable, '-c', 'pass'], os.environ)
        else:
            res = posix.waitid(posix.P_PID, pid, posix.WEXITED)
            self.assertEqual(pid, res.si_pid)

    @unittest.skipUnless(hasattr(os, 'fork'), "test needs os.fork()")
    def test_register_at_fork(self):
        with self.assertRaises(TypeError, msg="Positional args not allowed"):
            os.register_at_fork(lambda: None)
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(before=2)
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(after_in_child="three")
        with self.assertRaises(TypeError, msg="Args must be callable"):
            os.register_at_fork(after_in_parent=b"Five")
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(before=None)
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(after_in_child=None)
        with self.assertRaises(TypeError, msg="Args must not be None"):
            os.register_at_fork(after_in_parent=None)
        with self.assertRaises(TypeError, msg="Invalid arg was allowed"):
            # Ensure a combination of valid and invalid is an error.
            os.register_at_fork(before=None, after_in_parent=lambda: 3)
        with self.assertRaises(TypeError, msg="Invalid arg was allowed"):
            # Ensure a combination of valid and invalid is an error.
            os.register_at_fork(before=lambda: None, after_in_child='')
        # We test actual registrations in their own process so as not to
        # pollute this one.  There is no way to unregister for cleanup.
        code = """if 1:
            import os

            r, w = os.pipe()
            fin_r, fin_w = os.pipe()

            os.register_at_fork(before=lambda: os.write(w, b'A'))
            os.register_at_fork(after_in_parent=lambda: os.write(w, b'C'))
            os.register_at_fork(after_in_child=lambda: os.write(w, b'E'))
            os.register_at_fork(before=lambda: os.write(w, b'B'),
                                after_in_parent=lambda: os.write(w, b'D'),
                                after_in_child=lambda: os.write(w, b'F'))

            pid = os.fork()
            if pid == 0:
                # At this point, after-forkers have already been executed
                os.close(w)
                # Wait for parent to tell us to exit
                os.read(fin_r, 1)
                os._exit(0)
            else:
                try:
                    os.close(w)
                    with open(r, "rb") as f:
                        data = f.read()
                        assert len(data) == 6, data
                        # Check before-fork callbacks
                        assert data[:2] == b'BA', data
                        # Check after-fork callbacks
                        assert sorted(data[2:]) == list(b'CDEF'), data
                        assert data.index(b'C') < data.index(b'D'), data
                        assert data.index(b'E') < data.index(b'F'), data
                finally:
                    os.write(fin_w, b'!')
            """
        assert_python_ok('-c', code)

    @unittest.skipUnless(hasattr(posix, 'lockf'), "test needs posix.lockf()")
    def test_lockf(self):
        fd = os.open(support.TESTFN, os.O_WRONLY | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            posix.lockf(fd, posix.F_LOCK, 4)
            # section is locked
            posix.lockf(fd, posix.F_ULOCK, 4)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pread'), "test needs posix.pread()")
    def test_pread(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'es', posix.pread(fd, 2, 1))
            # the first pread() shouldn't disturb the file offset
            self.assertEqual(b'te', posix.read(fd, 2))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    def test_preadv(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3t5t6t6t8')
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.preadv(fd, buf, 3), 10)
            self.assertEqual([b't1tt2', b't3t', b'5t'], list(buf))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    @unittest.skipUnless(hasattr(posix, 'RWF_HIPRI'), "test needs posix.RWF_HIPRI")
    def test_preadv_flags(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3t5t6t6t8')
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.preadv(fd, buf, 3, os.RWF_HIPRI), 10)
            self.assertEqual([b't1tt2', b't3t', b'5t'], list(buf))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'preadv'), "test needs posix.preadv()")
    @requires_32b
    def test_preadv_overflow_32bits(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            buf = [bytearray(2**16)] * 2**15
            with self.assertRaises(OSError) as cm:
                os.preadv(fd, buf, 0)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
            self.assertEqual(bytes(buf[0]), b'\0'* 2**16)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwrite'), "test needs posix.pwrite()")
    def test_pwrite(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test')
            os.lseek(fd, 0, os.SEEK_SET)
            posix.pwrite(fd, b'xx', 1)
            self.assertEqual(b'txxt', posix.read(fd, 4))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    def test_pwritev(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b"xx")
            os.lseek(fd, 0, os.SEEK_SET)
            n = os.pwritev(fd, [b'test1', b'tt2', b't3'], 2)
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'xxtest1tt2t3', posix.read(fd, 100))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    @unittest.skipUnless(hasattr(posix, 'os.RWF_SYNC'), "test needs os.RWF_SYNC")
    def test_pwritev_flags(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd,b"xx")
            os.lseek(fd, 0, os.SEEK_SET)
            n = os.pwritev(fd, [b'test1', b'tt2', b't3'], 2, os.RWF_SYNC)
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'xxtest1tt2', posix.read(fd, 100))
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'pwritev'), "test needs posix.pwritev()")
    @requires_32b
    def test_pwritev_overflow_32bits(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            with self.assertRaises(OSError) as cm:
                os.pwritev(fd, [b"x" * 2**16] * 2**15, 0)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'posix_fallocate'),
        "test needs posix.posix_fallocate()")
    def test_posix_fallocate(self):
        fd = os.open(support.TESTFN, os.O_WRONLY | os.O_CREAT)
        try:
            posix.posix_fallocate(fd, 0, 10)
        except OSError as inst:
            # issue10812, ZFS doesn't appear to support posix_fallocate,
            # so skip Solaris-based since they are likely to have ZFS.
            # issue33655: Also ignore EINVAL on *BSD since ZFS is also
            # often used there.
            if inst.errno == errno.EINVAL and sys.platform.startswith(
                ('sunos', 'freebsd', 'netbsd', 'openbsd', 'gnukfreebsd')):
                raise unittest.SkipTest("test may fail on ZFS filesystems")
            else:
                raise
        finally:
            os.close(fd)

    # issue31106 - posix_fallocate() does not set error in errno.
    @unittest.skipUnless(hasattr(posix, 'posix_fallocate'),
        "test needs posix.posix_fallocate()")
    def test_posix_fallocate_errno(self):
        try:
            posix.posix_fallocate(-42, 0, 10)
        except OSError as inst:
            if inst.errno != errno.EBADF:
                raise

    @unittest.skipUnless(hasattr(posix, 'posix_fadvise'),
        "test needs posix.posix_fadvise()")
    def test_posix_fadvise(self):
        fd = os.open(support.TESTFN, os.O_RDONLY)
        try:
            posix.posix_fadvise(fd, 0, 0, posix.POSIX_FADV_WILLNEED)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'posix_fadvise'),
        "test needs posix.posix_fadvise()")
    def test_posix_fadvise_errno(self):
        try:
            posix.posix_fadvise(-42, 0, 0, posix.POSIX_FADV_WILLNEED)
        except OSError as inst:
            if inst.errno != errno.EBADF:
                raise

    @unittest.skipUnless(os.utime in os.supports_fd, "test needs fd support in os.utime")
    def test_utime_with_fd(self):
        now = time.time()
        fd = os.open(support.TESTFN, os.O_RDONLY)
        try:
            posix.utime(fd)
            posix.utime(fd, None)
            self.assertRaises(TypeError, posix.utime, fd, (None, None))
            self.assertRaises(TypeError, posix.utime, fd, (now, None))
            self.assertRaises(TypeError, posix.utime, fd, (None, now))
            posix.utime(fd, (int(now), int(now)))
            posix.utime(fd, (now, now))
            self.assertRaises(ValueError, posix.utime, fd, (now, now), ns=(now, now))
            self.assertRaises(ValueError, posix.utime, fd, (now, 0), ns=(None, None))
            self.assertRaises(ValueError, posix.utime, fd, (None, None), ns=(now, 0))
            posix.utime(fd, (int(now), int((now - int(now)) * 1e9)))
            posix.utime(fd, ns=(int(now), int((now - int(now)) * 1e9)))

        finally:
            os.close(fd)

    @unittest.skipUnless(os.utime in os.supports_follow_symlinks, "test needs follow_symlinks support in os.utime")
    def test_utime_nofollow_symlinks(self):
        now = time.time()
        posix.utime(support.TESTFN, None, follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, None), follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (now, None), follow_symlinks=False)
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, now), follow_symlinks=False)
        posix.utime(support.TESTFN, (int(now), int(now)), follow_symlinks=False)
        posix.utime(support.TESTFN, (now, now), follow_symlinks=False)
        posix.utime(support.TESTFN, follow_symlinks=False)

    @unittest.skipUnless(hasattr(posix, 'writev'), "test needs posix.writev()")
    def test_writev(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            n = os.writev(fd, (b'test1', b'tt2', b't3'))
            self.assertEqual(n, 10)

            os.lseek(fd, 0, os.SEEK_SET)
            self.assertEqual(b'test1tt2t3', posix.read(fd, 10))

            # Issue #20113: empty list of buffers should not crash
            try:
                size = posix.writev(fd, [])
            except OSError:
                # writev(fd, []) raises OSError(22, "Invalid argument")
                # on OpenIndiana
                pass
            else:
                self.assertEqual(size, 0)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'writev'), "test needs posix.writev()")
    @requires_32b
    def test_writev_overflow_32bits(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            with self.assertRaises(OSError) as cm:
                os.writev(fd, [b"x" * 2**16] * 2**15)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'readv'), "test needs posix.readv()")
    def test_readv(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            os.write(fd, b'test1tt2t3')
            os.lseek(fd, 0, os.SEEK_SET)
            buf = [bytearray(i) for i in [5, 3, 2]]
            self.assertEqual(posix.readv(fd, buf), 10)
            self.assertEqual([b'test1', b'tt2', b't3'], [bytes(i) for i in buf])

            # Issue #20113: empty list of buffers should not crash
            try:
                size = posix.readv(fd, [])
            except OSError:
                # readv(fd, []) raises OSError(22, "Invalid argument")
                # on OpenIndiana
                pass
            else:
                self.assertEqual(size, 0)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'readv'), "test needs posix.readv()")
    @requires_32b
    def test_readv_overflow_32bits(self):
        fd = os.open(support.TESTFN, os.O_RDWR | os.O_CREAT)
        try:
            buf = [bytearray(2**16)] * 2**15
            with self.assertRaises(OSError) as cm:
                os.readv(fd, buf)
            self.assertEqual(cm.exception.errno, errno.EINVAL)
            self.assertEqual(bytes(buf[0]), b'\0'* 2**16)
        finally:
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'dup'),
                         'test needs posix.dup()')
    def test_dup(self):
        fp = open(support.TESTFN)
        try:
            fd = posix.dup(fp.fileno())
            self.assertIsInstance(fd, int)
            os.close(fd)
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'confstr'),
                         'test needs posix.confstr()')
    def test_confstr(self):
        self.assertRaises(ValueError, posix.confstr, "CS_garbage")
        self.assertEqual(len(posix.confstr("CS_PATH")) > 0, True)

    @unittest.skipUnless(hasattr(posix, 'dup2'),
                         'test needs posix.dup2()')
    def test_dup2(self):
        fp1 = open(support.TESTFN)
        fp2 = open(support.TESTFN)
        try:
            posix.dup2(fp1.fileno(), fp2.fileno())
        finally:
            fp1.close()
            fp2.close()

    @unittest.skipUnless(hasattr(os, 'O_CLOEXEC'), "needs os.O_CLOEXEC")
    @support.requires_linux_version(2, 6, 23)
    def test_oscloexec(self):
        fd = os.open(support.TESTFN, os.O_RDONLY|os.O_CLOEXEC)
        self.addCleanup(os.close, fd)
        self.assertFalse(os.get_inheritable(fd))

    @unittest.skipUnless(hasattr(posix, 'O_EXLOCK'),
                         'test needs posix.O_EXLOCK')
    def test_osexlock(self):
        fd = os.open(support.TESTFN,
                     os.O_WRONLY|os.O_EXLOCK|os.O_CREAT)
        self.assertRaises(OSError, os.open, support.TESTFN,
                          os.O_WRONLY|os.O_EXLOCK|os.O_NONBLOCK)
        os.close(fd)

        if hasattr(posix, "O_SHLOCK"):
            fd = os.open(support.TESTFN,
                         os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
            self.assertRaises(OSError, os.open, support.TESTFN,
                              os.O_WRONLY|os.O_EXLOCK|os.O_NONBLOCK)
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'O_SHLOCK'),
                         'test needs posix.O_SHLOCK')
    def test_osshlock(self):
        fd1 = os.open(support.TESTFN,
                     os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
        fd2 = os.open(support.TESTFN,
                      os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
        os.close(fd2)
        os.close(fd1)

        if hasattr(posix, "O_EXLOCK"):
            fd = os.open(support.TESTFN,
                         os.O_WRONLY|os.O_SHLOCK|os.O_CREAT)
            self.assertRaises(OSError, os.open, support.TESTFN,
                              os.O_RDONLY|os.O_EXLOCK|os.O_NONBLOCK)
            os.close(fd)

    @unittest.skipUnless(hasattr(posix, 'fstat'),
                         'test needs posix.fstat()')
    def test_fstat(self):
        fp = open(support.TESTFN)
        try:
            self.assertTrue(posix.fstat(fp.fileno()))
            self.assertTrue(posix.stat(fp.fileno()))

            self.assertRaisesRegex(TypeError,
                    'should be string, bytes, os.PathLike or integer, not',
                    posix.stat, float(fp.fileno()))
        finally:
            fp.close()

    @unittest.skipUnless(hasattr(posix, 'stat'),
                         'test needs posix.stat()')
    def test_stat(self):
        self.assertTrue(posix.stat(support.TESTFN))
        self.assertTrue(posix.stat(os.fsencode(support.TESTFN)))

        self.assertWarnsRegex(DeprecationWarning,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, bytearray(os.fsencode(support.TESTFN)))
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, None)
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, list(support.TESTFN))
        self.assertRaisesRegex(TypeError,
                'should be string, bytes, os.PathLike or integer, not',
                posix.stat, list(os.fsencode(support.TESTFN)))

    @unittest.skipUnless(hasattr(posix, 'mkfifo'), "don't have mkfifo()")
    def test_mkfifo(self):
        support.unlink(support.TESTFN)
        try:
            posix.mkfifo(support.TESTFN, stat.S_IRUSR | stat.S_IWUSR)
        except PermissionError as e:
            self.skipTest('posix.mkfifo(): %s' % e)
        self.assertTrue(stat.S_ISFIFO(posix.stat(support.TESTFN).st_mode))

    @unittest.skipUnless(hasattr(posix, 'mknod') and hasattr(stat, 'S_IFIFO'),
                         "don't have mknod()/S_IFIFO")
    def test_mknod(self):
        # Test using mknod() to create a FIFO (the only use specified
        # by POSIX).
        support.unlink(support.TESTFN)
        mode = stat.S_IFIFO | stat.S_IRUSR | stat.S_IWUSR
        try:
            posix.mknod(support.TESTFN, mode, 0)
        except OSError as e:
            # Some old systems don't allow unprivileged users to use
            # mknod(), or only support creating device nodes.
            self.assertIn(e.errno, (errno.EPERM, errno.EINVAL, errno.EACCES))
        else:
            self.assertTrue(stat.S_ISFIFO(posix.stat(support.TESTFN).st_mode))

        # Keyword arguments are also supported
        support.unlink(support.TESTFN)
        try:
            posix.mknod(path=support.TESTFN, mode=mode, device=0,
                dir_fd=None)
        except OSError as e:
            self.assertIn(e.errno, (errno.EPERM, errno.EINVAL, errno.EACCES))

    @unittest.skipUnless(hasattr(posix, 'stat'), 'test needs posix.stat()')
    @unittest.skipUnless(hasattr(posix, 'makedev'), 'test needs posix.makedev()')
    def test_makedev(self):
        st = posix.stat(support.TESTFN)
        dev = st.st_dev
        self.assertIsInstance(dev, int)
        self.assertGreaterEqual(dev, 0)

        major = posix.major(dev)
        self.assertIsInstance(major, int)
        self.assertGreaterEqual(major, 0)
        self.assertEqual(posix.major(dev), major)
        self.assertRaises(TypeError, posix.major, float(dev))
        self.assertRaises(TypeError, posix.major)
        self.assertRaises((ValueError, OverflowError), posix.major, -1)

        minor = posix.minor(dev)
        self.assertIsInstance(minor, int)
        self.assertGreaterEqual(minor, 0)
        self.assertEqual(posix.minor(dev), minor)
        self.assertRaises(TypeError, posix.minor, float(dev))
        self.assertRaises(TypeError, posix.minor)
        self.assertRaises((ValueError, OverflowError), posix.minor, -1)

        self.assertEqual(posix.makedev(major, minor), dev)
        self.assertRaises(TypeError, posix.makedev, float(major), minor)
        self.assertRaises(TypeError, posix.makedev, major, float(minor))
        self.assertRaises(TypeError, posix.makedev, major)
        self.assertRaises(TypeError, posix.makedev)

    def _test_all_chown_common(self, chown_func, first_param, stat_func):
        """Common code for chown, fchown and lchown tests."""
        def check_stat(uid, gid):
            if stat_func is not None:
                stat = stat_func(first_param)
                self.assertEqual(stat.st_uid, uid)
                self.assertEqual(stat.st_gid, gid)
        uid = os.getuid()
        gid = os.getgid()
        # test a successful chown call
        chown_func(first_param, uid, gid)
        check_stat(uid, gid)
        chown_func(first_param, -1, gid)
        check_stat(uid, gid)
        chown_func(first_param, uid, -1)
        check_stat(uid, gid)

        if uid == 0:
            # Try an amusingly large uid/gid to make sure we handle
            # large unsigned values.  (chown lets you use any
            # uid/gid you like, even if they aren't defined.)
            #
            # This problem keeps coming up:
            #   http://bugs.python.org/issue1747858
            #   http://bugs.python.org/issue4591
            #   http://bugs.python.org/issue15301
            # Hopefully the fix in 4591 fixes it for good!
            #
            # This part of the test only runs when run as root.
            # Only scary people run their tests as root.

            big_value = 2**31
            chown_func(first_param, big_value, big_value)
            check_stat(big_value, big_value)
            chown_func(first_param, -1, -1)
            check_stat(big_value, big_value)
            chown_func(first_param, uid, gid)
            check_stat(uid, gid)
        elif platform.system() in ('HP-UX', 'SunOS'):
            # HP-UX and Solaris can allow a non-root user to chown() to root
            # (issue #5113)
            raise unittest.SkipTest("Skipping because of non-standard chown() "
                                    "behavior")
        else:
            # non-root cannot chown to root, raises OSError
            self.assertRaises(OSError, chown_func, first_param, 0, 0)
            check_stat(uid, gid)
            self.assertRaises(OSError, chown_func, first_param, 0, -1)
            check_stat(uid, gid)
            if 0 not in os.getgroups():
                self.assertRaises(OSError, chown_func, first_param, -1, 0)
                check_stat(uid, gid)
        # test illegal types
        for t in str, float:
            self.assertRaises(TypeError, chown_func, first_param, t(uid), gid)
            check_stat(uid, gid)
            self.assertRaises(TypeError, chown_func, first_param, uid, t(gid))
            check_stat(uid, gid)

    @unittest.skipUnless(hasattr(posix, 'chown'), "test needs os.chown()")
    def test_chown(self):
        # raise an OSError if the file does not exist
        os.unlink(support.TESTFN)
        self.assertRaises(OSError, posix.chown, support.TESTFN, -1, -1)

        # re-create the file
        support.create_empty_file(support.TESTFN)
        self._test_all_chown_common(posix.chown, support.TESTFN,
                                    getattr(posix, 'stat', None))

    @unittest.skipUnless(hasattr(posix, 'fchown'), "test needs os.fchown()")
    def test_fchown(self):
        os.unlink(support.TESTFN)

        # re-create the file
        test_file = open(support.TESTFN, 'w')
        try:
            fd = test_file.fileno()
            self._test_all_chown_common(posix.fchown, fd,
                                        getattr(posix, 'fstat', None))
        finally:
            test_file.close()

    @unittest.skipUnless(hasattr(posix, 'lchown'), "test needs os.lchown()")
    def test_lchown(self):
        os.unlink(support.TESTFN)
        # create a symlink
        os.symlink(_DUMMY_SYMLINK, support.TESTFN)
        self._test_all_chown_common(posix.lchown, support.TESTFN,
                                    getattr(posix, 'lstat', None))

    @unittest.skipUnless(hasattr(posix, 'chdir'), 'test needs posix.chdir()')
    def test_chdir(self):
        posix.chdir(os.curdir)
        self.assertRaises(OSError, posix.chdir, support.TESTFN)

    def test_listdir(self):
        self.assertIn(support.TESTFN, posix.listdir(os.curdir))

    def test_listdir_default(self):
        # When listdir is called without argument,
        # it's the same as listdir(os.curdir).
        self.assertIn(support.TESTFN, posix.listdir())

    def test_listdir_bytes(self):
        # When listdir is called with a bytes object,
        # the returned strings are of type bytes.
        self.assertIn(os.fsencode(support.TESTFN), posix.listdir(b'.'))

    def test_listdir_bytes_like(self):
        for cls in bytearray, memoryview:
            with self.assertWarns(DeprecationWarning):
                names = posix.listdir(cls(b'.'))
            self.assertIn(os.fsencode(support.TESTFN), names)
            for name in names:
                self.assertIs(type(name), bytes)

    @unittest.skipUnless(posix.listdir in os.supports_fd,
                         "test needs fd support for posix.listdir()")
    def test_listdir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        self.addCleanup(posix.close, f)
        self.assertEqual(
            sorted(posix.listdir('.')),
            sorted(posix.listdir(f))
            )
        # Check that the fd offset was reset (issue #13739)
        self.assertEqual(
            sorted(posix.listdir('.')),
            sorted(posix.listdir(f))
            )

    @unittest.skipUnless(hasattr(posix, 'access'), 'test needs posix.access()')
    def test_access(self):
        self.assertTrue(posix.access(support.TESTFN, os.R_OK))

    @unittest.skipUnless(hasattr(posix, 'umask'), 'test needs posix.umask()')
    def test_umask(self):
        old_mask = posix.umask(0)
        self.assertIsInstance(old_mask, int)
        posix.umask(old_mask)

    @unittest.skipUnless(hasattr(posix, 'strerror'),
                         'test needs posix.strerror()')
    def test_strerror(self):
        self.assertTrue(posix.strerror(0))

    @unittest.skipUnless(hasattr(posix, 'pipe'), 'test needs posix.pipe()')
    def test_pipe(self):
        reader, writer = posix.pipe()
        os.close(reader)
        os.close(writer)

    @unittest.skipUnless(hasattr(os, 'pipe2'), "test needs os.pipe2()")
    @support.requires_linux_version(2, 6, 27)
    def test_pipe2(self):
        self.assertRaises(TypeError, os.pipe2, 'DEADBEEF')
        self.assertRaises(TypeError, os.pipe2, 0, 0)

        # try calling with flags = 0, like os.pipe()
        r, w = os.pipe2(0)
        os.close(r)
        os.close(w)

        # test flags
        r, w = os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK)
        self.addCleanup(os.close, r)
        self.addCleanup(os.close, w)
        self.assertFalse(os.get_inheritable(r))
        self.assertFalse(os.get_inheritable(w))
        self.assertFalse(os.get_blocking(r))
        self.assertFalse(os.get_blocking(w))
        # try reading from an empty pipe: this should fail, not block
        self.assertRaises(OSError, os.read, r, 1)
        # try a write big enough to fill-up the pipe: this should either
        # fail or perform a partial write, not block
        try:
            os.write(w, b'x' * support.PIPE_MAX_SIZE)
        except OSError:
            pass

    @support.cpython_only
    @unittest.skipUnless(hasattr(os, 'pipe2'), "test needs os.pipe2()")
    @support.requires_linux_version(2, 6, 27)
    def test_pipe2_c_limits(self):
        # Issue 15989
        import _testcapi
        self.assertRaises(OverflowError, os.pipe2, _testcapi.INT_MAX + 1)
        self.assertRaises(OverflowError, os.pipe2, _testcapi.UINT_MAX + 1)

    @unittest.skipUnless(hasattr(posix, 'utime'), 'test needs posix.utime()')
    def test_utime(self):
        now = time.time()
        posix.utime(support.TESTFN, None)
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, None))
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (now, None))
        self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, now))
        posix.utime(support.TESTFN, (int(now), int(now)))
        posix.utime(support.TESTFN, (now, now))

    def _test_chflags_regular_file(self, chflags_func, target_file, **kwargs):
        st = os.stat(target_file)
        self.assertTrue(hasattr(st, 'st_flags'))

        # ZFS returns EOPNOTSUPP when attempting to set flag UF_IMMUTABLE.
        flags = st.st_flags | stat.UF_IMMUTABLE
        try:
            chflags_func(target_file, flags, **kwargs)
        except OSError as err:
            if err.errno != errno.EOPNOTSUPP:
                raise
            msg = 'chflag UF_IMMUTABLE not supported by underlying fs'
            self.skipTest(msg)

        try:
            new_st = os.stat(target_file)
            self.assertEqual(st.st_flags | stat.UF_IMMUTABLE, new_st.st_flags)
            try:
                fd = open(target_file, 'w+')
            except OSError as e:
                self.assertEqual(e.errno, errno.EPERM)
        finally:
            posix.chflags(target_file, st.st_flags)

    @unittest.skipUnless(hasattr(posix, 'chflags'), 'test needs os.chflags()')
    def test_chflags(self):
        self._test_chflags_regular_file(posix.chflags, support.TESTFN)

    @unittest.skipUnless(hasattr(posix, 'lchflags'), 'test needs os.lchflags()')
    def test_lchflags_regular_file(self):
        self._test_chflags_regular_file(posix.lchflags, support.TESTFN)
        self._test_chflags_regular_file(posix.chflags, support.TESTFN, follow_symlinks=False)

    @unittest.skipUnless(hasattr(posix, 'lchflags'), 'test needs os.lchflags()')
    def test_lchflags_symlink(self):
        testfn_st = os.stat(support.TESTFN)

        self.assertTrue(hasattr(testfn_st, 'st_flags'))

        os.symlink(support.TESTFN, _DUMMY_SYMLINK)
        self.teardown_files.append(_DUMMY_SYMLINK)
        dummy_symlink_st = os.lstat(_DUMMY_SYMLINK)

        def chflags_nofollow(path, flags):
            return posix.chflags(path, flags, follow_symlinks=False)

        for fn in (posix.lchflags, chflags_nofollow):
            # ZFS returns EOPNOTSUPP when attempting to set flag UF_IMMUTABLE.
            flags = dummy_symlink_st.st_flags | stat.UF_IMMUTABLE
            try:
                fn(_DUMMY_SYMLINK, flags)
            except OSError as err:
                if err.errno != errno.EOPNOTSUPP:
                    raise
                msg = 'chflag UF_IMMUTABLE not supported by underlying fs'
                self.skipTest(msg)
            try:
                new_testfn_st = os.stat(support.TESTFN)
                new_dummy_symlink_st = os.lstat(_DUMMY_SYMLINK)

                self.assertEqual(testfn_st.st_flags, new_testfn_st.st_flags)
                self.assertEqual(dummy_symlink_st.st_flags | stat.UF_IMMUTABLE,
                                 new_dummy_symlink_st.st_flags)
            finally:
                fn(_DUMMY_SYMLINK, dummy_symlink_st.st_flags)

    def test_environ(self):
        if os.name == "nt":
            item_type = str
        else:
            item_type = bytes
        for k, v in posix.environ.items():
            self.assertEqual(type(k), item_type)
            self.assertEqual(type(v), item_type)

    @unittest.skipUnless(hasattr(os, "putenv"), "requires os.putenv()")
    def test_putenv(self):
        with self.assertRaises(ValueError):
            os.putenv('FRUIT\0VEGETABLE', 'cabbage')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT\0VEGETABLE', b'cabbage')
        with self.assertRaises(ValueError):
            os.putenv('FRUIT', 'orange\0VEGETABLE=cabbage')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT', b'orange\0VEGETABLE=cabbage')
        with self.assertRaises(ValueError):
            os.putenv('FRUIT=ORANGE', 'lemon')
        with self.assertRaises(ValueError):
            os.putenv(b'FRUIT=ORANGE', b'lemon')

    @unittest.skipUnless(hasattr(posix, 'getcwd'), 'test needs posix.getcwd()')
    def test_getcwd_long_pathnames(self):
        dirname = 'getcwd-test-directory-0123456789abcdef-01234567890abcdef'
        curdir = os.getcwd()
        base_path = os.path.abspath(support.TESTFN) + '.getcwd'

        try:
            os.mkdir(base_path)
            os.chdir(base_path)
        except:
            #  Just returning nothing instead of the SkipTest exception, because
            #  the test results in Error in that case.  Is that ok?
            #  raise unittest.SkipTest("cannot create directory for testing")
            return

            def _create_and_do_getcwd(dirname, current_path_length = 0):
                try:
                    os.mkdir(dirname)
                except:
                    raise unittest.SkipTest("mkdir cannot create directory sufficiently deep for getcwd test")

                os.chdir(dirname)
                try:
                    os.getcwd()
                    if current_path_length < 1027:
                        _create_and_do_getcwd(dirname, current_path_length + len(dirname) + 1)
                finally:
                    os.chdir('..')
                    os.rmdir(dirname)

            _create_and_do_getcwd(dirname)

        finally:
            os.chdir(curdir)
            support.rmtree(base_path)

    @unittest.skipUnless(hasattr(posix, 'getgrouplist'), "test needs posix.getgrouplist()")
    @unittest.skipUnless(hasattr(pwd, 'getpwuid'), "test needs pwd.getpwuid()")
    @unittest.skipUnless(hasattr(os, 'getuid'), "test needs os.getuid()")
    def test_getgrouplist(self):
        user = pwd.getpwuid(os.getuid())[0]
        group = pwd.getpwuid(os.getuid())[3]
        self.assertIn(group, posix.getgrouplist(user, group))


    @unittest.skipUnless(hasattr(os, 'getegid'), "test needs os.getegid()")
    def test_getgroups(self):
        with os.popen('id -G 2>/dev/null') as idg:
            groups = idg.read().strip()
            ret = idg.close()

        try:
            idg_groups = set(int(g) for g in groups.split())
        except ValueError:
            idg_groups = set()
        if ret is not None or not idg_groups:
            raise unittest.SkipTest("need working 'id -G'")

        # Issues 16698: OS X ABIs prior to 10.6 have limits on getgroups()
        if sys.platform == 'darwin':
            import sysconfig
            dt = sysconfig.get_config_var('MACOSX_DEPLOYMENT_TARGET') or '10.0'
            if tuple(int(n) for n in dt.split('.')[0:2]) < (10, 6):
                raise unittest.SkipTest("getgroups(2) is broken prior to 10.6")

        # 'id -G' and 'os.getgroups()' should return the same
        # groups, ignoring order, duplicates, and the effective gid.
        # #10822/#26944 - It is implementation defined whether
        # posix.getgroups() includes the effective gid.
        symdiff = idg_groups.symmetric_difference(posix.getgroups())
        self.assertTrue(not symdiff or symdiff == {posix.getegid()})

    # tests for the posix *at functions follow

    @unittest.skipUnless(os.access in os.supports_dir_fd, "test needs dir_fd support for os.access()")
    def test_access_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            self.assertTrue(posix.access(support.TESTFN, os.R_OK, dir_fd=f))
        finally:
            posix.close(f)

    @unittest.skipUnless(os.chmod in os.supports_dir_fd, "test needs dir_fd support in os.chmod()")
    def test_chmod_dir_fd(self):
        os.chmod(support.TESTFN, stat.S_IRUSR)

        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.chmod(support.TESTFN, stat.S_IRUSR | stat.S_IWUSR, dir_fd=f)

            s = posix.stat(support.TESTFN)
            self.assertEqual(s[0] & stat.S_IRWXU, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            posix.close(f)

    @unittest.skipUnless(os.chown in os.supports_dir_fd, "test needs dir_fd support in os.chown()")
    def test_chown_dir_fd(self):
        support.unlink(support.TESTFN)
        support.create_empty_file(support.TESTFN)

        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.chown(support.TESTFN, os.getuid(), os.getgid(), dir_fd=f)
        finally:
            posix.close(f)

    @unittest.skipUnless(os.stat in os.supports_dir_fd, "test needs dir_fd support in os.stat()")
    def test_stat_dir_fd(self):
        support.unlink(support.TESTFN)
        with open(support.TESTFN, 'w') as outfile:
            outfile.write("testline\n")

        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            s1 = posix.stat(support.TESTFN)
            s2 = posix.stat(support.TESTFN, dir_fd=f)
            self.assertEqual(s1, s2)
            s2 = posix.stat(support.TESTFN, dir_fd=None)
            self.assertEqual(s1, s2)
            self.assertRaisesRegex(TypeError, 'should be integer or None, not',
                    posix.stat, support.TESTFN, dir_fd=posix.getcwd())
            self.assertRaisesRegex(TypeError, 'should be integer or None, not',
                    posix.stat, support.TESTFN, dir_fd=float(f))
            self.assertRaises(OverflowError,
                    posix.stat, support.TESTFN, dir_fd=10**20)
        finally:
            posix.close(f)

    @unittest.skipUnless(os.utime in os.supports_dir_fd, "test needs dir_fd support in os.utime()")
    def test_utime_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            now = time.time()
            posix.utime(support.TESTFN, None, dir_fd=f)
            posix.utime(support.TESTFN, dir_fd=f)
            self.assertRaises(TypeError, posix.utime, support.TESTFN, now, dir_fd=f)
            self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, None), dir_fd=f)
            self.assertRaises(TypeError, posix.utime, support.TESTFN, (now, None), dir_fd=f)
            self.assertRaises(TypeError, posix.utime, support.TESTFN, (None, now), dir_fd=f)
            self.assertRaises(TypeError, posix.utime, support.TESTFN, (now, "x"), dir_fd=f)
            posix.utime(support.TESTFN, (int(now), int(now)), dir_fd=f)
            posix.utime(support.TESTFN, (now, now), dir_fd=f)
            posix.utime(support.TESTFN,
                    (int(now), int((now - int(now)) * 1e9)), dir_fd=f)
            posix.utime(support.TESTFN, dir_fd=f,
                            times=(int(now), int((now - int(now)) * 1e9)))

            # try dir_fd and follow_symlinks together
            if os.utime in os.supports_follow_symlinks:
                try:
                    posix.utime(support.TESTFN, follow_symlinks=False, dir_fd=f)
                except ValueError:
                    # whoops!  using both together not supported on this platform.
                    pass

        finally:
            posix.close(f)

    @unittest.skipUnless(os.link in os.supports_dir_fd, "test needs dir_fd support in os.link()")
    def test_link_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.link(support.TESTFN, support.TESTFN + 'link', src_dir_fd=f, dst_dir_fd=f)
        except PermissionError as e:
            self.skipTest('posix.link(): %s' % e)
        else:
            # should have same inodes
            self.assertEqual(posix.stat(support.TESTFN)[1],
                posix.stat(support.TESTFN + 'link')[1])
        finally:
            posix.close(f)
            support.unlink(support.TESTFN + 'link')

    @unittest.skipUnless(os.mkdir in os.supports_dir_fd, "test needs dir_fd support in os.mkdir()")
    def test_mkdir_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.mkdir(support.TESTFN + 'dir', dir_fd=f)
            posix.stat(support.TESTFN + 'dir') # should not raise exception
        finally:
            posix.close(f)
            support.rmtree(support.TESTFN + 'dir')

    @unittest.skipUnless((os.mknod in os.supports_dir_fd) and hasattr(stat, 'S_IFIFO'),
                         "test requires both stat.S_IFIFO and dir_fd support for os.mknod()")
    def test_mknod_dir_fd(self):
        # Test using mknodat() to create a FIFO (the only use specified
        # by POSIX).
        support.unlink(support.TESTFN)
        mode = stat.S_IFIFO | stat.S_IRUSR | stat.S_IWUSR
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.mknod(support.TESTFN, mode, 0, dir_fd=f)
        except OSError as e:
            # Some old systems don't allow unprivileged users to use
            # mknod(), or only support creating device nodes.
            self.assertIn(e.errno, (errno.EPERM, errno.EINVAL, errno.EACCES))
        else:
            self.assertTrue(stat.S_ISFIFO(posix.stat(support.TESTFN).st_mode))
        finally:
            posix.close(f)

    @unittest.skipUnless(os.open in os.supports_dir_fd, "test needs dir_fd support in os.open()")
    def test_open_dir_fd(self):
        support.unlink(support.TESTFN)
        with open(support.TESTFN, 'w') as outfile:
            outfile.write("testline\n")
        a = posix.open(posix.getcwd(), posix.O_RDONLY)
        b = posix.open(support.TESTFN, posix.O_RDONLY, dir_fd=a)
        try:
            res = posix.read(b, 9).decode(encoding="utf-8")
            self.assertEqual("testline\n", res)
        finally:
            posix.close(a)
            posix.close(b)

    @unittest.skipUnless(os.readlink in os.supports_dir_fd, "test needs dir_fd support in os.readlink()")
    def test_readlink_dir_fd(self):
        os.symlink(support.TESTFN, support.TESTFN + 'link')
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            self.assertEqual(posix.readlink(support.TESTFN + 'link'),
                posix.readlink(support.TESTFN + 'link', dir_fd=f))
        finally:
            support.unlink(support.TESTFN + 'link')
            posix.close(f)

    @unittest.skipUnless(os.rename in os.supports_dir_fd, "test needs dir_fd support in os.rename()")
    def test_rename_dir_fd(self):
        support.unlink(support.TESTFN)
        support.create_empty_file(support.TESTFN + 'ren')
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.rename(support.TESTFN + 'ren', support.TESTFN, src_dir_fd=f, dst_dir_fd=f)
        except:
            posix.rename(support.TESTFN + 'ren', support.TESTFN)
            raise
        else:
            posix.stat(support.TESTFN) # should not raise exception
        finally:
            posix.close(f)

    @unittest.skipUnless(os.symlink in os.supports_dir_fd, "test needs dir_fd support in os.symlink()")
    def test_symlink_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            posix.symlink(support.TESTFN, support.TESTFN + 'link', dir_fd=f)
            self.assertEqual(posix.readlink(support.TESTFN + 'link'), support.TESTFN)
        finally:
            posix.close(f)
            support.unlink(support.TESTFN + 'link')

    @unittest.skipUnless(os.unlink in os.supports_dir_fd, "test needs dir_fd support in os.unlink()")
    def test_unlink_dir_fd(self):
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        support.create_empty_file(support.TESTFN + 'del')
        posix.stat(support.TESTFN + 'del') # should not raise exception
        try:
            posix.unlink(support.TESTFN + 'del', dir_fd=f)
        except:
            support.unlink(support.TESTFN + 'del')
            raise
        else:
            self.assertRaises(OSError, posix.stat, support.TESTFN + 'link')
        finally:
            posix.close(f)

    @unittest.skipUnless(os.mkfifo in os.supports_dir_fd, "test needs dir_fd support in os.mkfifo()")
    def test_mkfifo_dir_fd(self):
        support.unlink(support.TESTFN)
        f = posix.open(posix.getcwd(), posix.O_RDONLY)
        try:
            try:
                posix.mkfifo(support.TESTFN,
                             stat.S_IRUSR | stat.S_IWUSR, dir_fd=f)
            except PermissionError as e:
                self.skipTest('posix.mkfifo(): %s' % e)
            self.assertTrue(stat.S_ISFIFO(posix.stat(support.TESTFN).st_mode))
        finally:
            posix.close(f)

    requires_sched_h = unittest.skipUnless(hasattr(posix, 'sched_yield'),
                                           "don't have scheduling support")
    requires_sched_affinity = unittest.skipUnless(hasattr(posix, 'sched_setaffinity'),
                                                  "don't have sched affinity support")

    @requires_sched_h
    def test_sched_yield(self):
        # This has no error conditions (at least on Linux).
        posix.sched_yield()

    @requires_sched_h
    @unittest.skipUnless(hasattr(posix, 'sched_get_priority_max'),
                         "requires sched_get_priority_max()")
    def test_sched_priority(self):
        # Round-robin usually has interesting priorities.
        pol = posix.SCHED_RR
        lo = posix.sched_get_priority_min(pol)
        hi = posix.sched_get_priority_max(pol)
        self.assertIsInstance(lo, int)
        self.assertIsInstance(hi, int)
        self.assertGreaterEqual(hi, lo)
        # OSX evidently just returns 15 without checking the argument.
        if sys.platform != "darwin":
            self.assertRaises(OSError, posix.sched_get_priority_min, -23)
            self.assertRaises(OSError, posix.sched_get_priority_max, -23)

    @requires_sched
    def test_get_and_set_scheduler_and_param(self):
        possible_schedulers = [sched for name, sched in posix.__dict__.items()
                               if name.startswith("SCHED_")]
        mine = posix.sched_getscheduler(0)
        self.assertIn(mine, possible_schedulers)
        try:
            parent = posix.sched_getscheduler(os.getppid())
        except OSError as e:
            if e.errno != errno.EPERM:
                raise
        else:
            self.assertIn(parent, possible_schedulers)
        self.assertRaises(OSError, posix.sched_getscheduler, -1)
        self.assertRaises(OSError, posix.sched_getparam, -1)
        param = posix.sched_getparam(0)
        self.assertIsInstance(param.sched_priority, int)

        # POSIX states that calling sched_setparam() or sched_setscheduler() on
        # a process with a scheduling policy other than SCHED_FIFO or SCHED_RR
        # is implementation-defined: NetBSD and FreeBSD can return EINVAL.
        if not sys.platform.startswith(('freebsd', 'netbsd')):
            try:
                posix.sched_setscheduler(0, mine, param)
                posix.sched_setparam(0, param)
            except OSError as e:
                if e.errno != errno.EPERM:
                    raise
            self.assertRaises(OSError, posix.sched_setparam, -1, param)

        self.assertRaises(OSError, posix.sched_setscheduler, -1, mine, param)
        self.assertRaises(TypeError, posix.sched_setscheduler, 0, mine, None)
        self.assertRaises(TypeError, posix.sched_setparam, 0, 43)
        param = posix.sched_param(None)
        self.assertRaises(TypeError, posix.sched_setparam, 0, param)
        large = 214748364700
        param = posix.sched_param(large)
        self.assertRaises(OverflowError, posix.sched_setparam, 0, param)
        param = posix.sched_param(sched_priority=-large)
        self.assertRaises(OverflowError, posix.sched_setparam, 0, param)

    @unittest.skipUnless(hasattr(posix, "sched_rr_get_interval"), "no function")
    def test_sched_rr_get_interval(self):
        try:
            interval = posix.sched_rr_get_interval(0)
        except OSError as e:
            # This likely means that sched_rr_get_interval is only valid for
            # processes with the SCHED_RR scheduler in effect.
            if e.errno != errno.EINVAL:
                raise
            self.skipTest("only works on SCHED_RR processes")
        self.assertIsInstance(interval, float)
        # Reasonable constraints, I think.
        self.assertGreaterEqual(interval, 0.)
        self.assertLess(interval, 1.)

    @requires_sched_affinity
    def test_sched_getaffinity(self):
        mask = posix.sched_getaffinity(0)
        self.assertIsInstance(mask, set)
        self.assertGreaterEqual(len(mask), 1)
        self.assertRaises(OSError, posix.sched_getaffinity, -1)
        for cpu in mask:
            self.assertIsInstance(cpu, int)
            self.assertGreaterEqual(cpu, 0)
            self.assertLess(cpu, 1 << 32)

    @requires_sched_affinity
    def test_sched_setaffinity(self):
        mask = posix.sched_getaffinity(0)
        if len(mask) > 1:
            # Empty masks are forbidden
            mask.pop()
        posix.sched_setaffinity(0, mask)
        self.assertEqual(posix.sched_getaffinity(0), mask)
        self.assertRaises(OSError, posix.sched_setaffinity, 0, [])
        self.assertRaises(ValueError, posix.sched_setaffinity, 0, [-10])
        self.assertRaises(OverflowError, posix.sched_setaffinity, 0, [1<<128])
        self.assertRaises(OSError, posix.sched_setaffinity, -1, mask)

    def test_rtld_constants(self):
        # check presence of major RTLD_* constants
        posix.RTLD_LAZY
        posix.RTLD_NOW
        posix.RTLD_GLOBAL
        posix.RTLD_LOCAL

    @unittest.skipUnless(hasattr(os, 'SEEK_HOLE'),
                         "test needs an OS that reports file holes")
    def test_fs_holes(self):
        # Even if the filesystem doesn't report holes,
        # if the OS supports it the SEEK_* constants
        # will be defined and will have a consistent
        # behaviour:
        # os.SEEK_DATA = current position
        # os.SEEK_HOLE = end of file position
        with open(support.TESTFN, 'r+b') as fp:
            fp.write(b"hello")
            fp.flush()
            size = fp.tell()
            fno = fp.fileno()
            try :
                for i in range(size):
                    self.assertEqual(i, os.lseek(fno, i, os.SEEK_DATA))
                    self.assertLessEqual(size, os.lseek(fno, i, os.SEEK_HOLE))
                self.assertRaises(OSError, os.lseek, fno, size, os.SEEK_DATA)
                self.assertRaises(OSError, os.lseek, fno, size, os.SEEK_HOLE)
            except OSError :
                # Some OSs claim to support SEEK_HOLE/SEEK_DATA
                # but it is not true.
                # For instance:
                # http://lists.freebsd.org/pipermail/freebsd-amd64/2012-January/014332.html
                raise unittest.SkipTest("OSError raised!")

    def test_path_error2(self):
        """
        Test functions that call path_error2(), providing two filenames in their exceptions.
        """
        for name in ("rename", "replace", "link"):
            function = getattr(os, name, None)
            if function is None:
                continue

            for dst in ("noodly2", support.TESTFN):
                try:
                    function('doesnotexistfilename', dst)
                except OSError as e:
                    self.assertIn("'doesnotexistfilename' -> '{}'".format(dst), str(e))
                    break
            else:
                self.fail("No valid path_error2() test for os." + name)

    def test_path_with_null_character(self):
        fn = support.TESTFN
        fn_with_NUL = fn + '\0'
        self.addCleanup(support.unlink, fn)
        support.unlink(fn)
        fd = None
        try:
            with self.assertRaises(ValueError):
                fd = os.open(fn_with_NUL, os.O_WRONLY | os.O_CREAT) # raises
        finally:
            if fd is not None:
                os.close(fd)
        self.assertFalse(os.path.exists(fn))
        self.assertRaises(ValueError, os.mkdir, fn_with_NUL)
        self.assertFalse(os.path.exists(fn))
        open(fn, 'wb').close()
        self.assertRaises(ValueError, os.stat, fn_with_NUL)

    def test_path_with_null_byte(self):
        fn = os.fsencode(support.TESTFN)
        fn_with_NUL = fn + b'\0'
        self.addCleanup(support.unlink, fn)
        support.unlink(fn)
        fd = None
        try:
            with self.assertRaises(ValueError):
                fd = os.open(fn_with_NUL, os.O_WRONLY | os.O_CREAT) # raises
        finally:
            if fd is not None:
                os.close(fd)
        self.assertFalse(os.path.exists(fn))
        self.assertRaises(ValueError, os.mkdir, fn_with_NUL)
        self.assertFalse(os.path.exists(fn))
        open(fn, 'wb').close()
        self.assertRaises(ValueError, os.stat, fn_with_NUL)

class PosixGroupsTester(unittest.TestCase):

    def setUp(self):
        if posix.getuid() != 0:
            raise unittest.SkipTest("not enough privileges")
        if not hasattr(posix, 'getgroups'):
            raise unittest.SkipTest("need posix.getgroups")
        if sys.platform == 'darwin':
            raise unittest.SkipTest("getgroups(2) is broken on OSX")
        self.saved_groups = posix.getgroups()

    def tearDown(self):
        if hasattr(posix, 'setgroups'):
            posix.setgroups(self.saved_groups)
        elif hasattr(posix, 'initgroups'):
            name = pwd.getpwuid(posix.getuid()).pw_name
            posix.initgroups(name, self.saved_groups[0])

    @unittest.skipUnless(hasattr(posix, 'initgroups'),
                         "test needs posix.initgroups()")
    def test_initgroups(self):
        # find missing group

        g = max(self.saved_groups or [0]) + 1
        name = pwd.getpwuid(posix.getuid()).pw_name
        posix.initgroups(name, g)
        self.assertIn(g, posix.getgroups())

    @unittest.skipUnless(hasattr(posix, 'setgroups'),
                         "test needs posix.setgroups()")
    def test_setgroups(self):
        for groups in [[0], list(range(16))]:
            posix.setgroups(groups)
            self.assertListEqual(groups, posix.getgroups())


@unittest.skipUnless(hasattr(os, 'posix_spawn'), "test needs os.posix_spawn")
class TestPosixSpawn(unittest.TestCase):
    # Program which does nothing and exit with status 0 (success)
    NOOP_PROGRAM = (sys.executable, '-I', '-S', '-c', 'pass')

    def python_args(self, *args):
        # Disable site module to avoid side effects. For example,
        # on Fedora 28, if the HOME environment variable is not set,
        # site._getuserbase() calls pwd.getpwuid() which opens
        # /var/lib/sss/mc/passwd but then leaves the file open which makes
        # test_close_file() to fail.
        return (sys.executable, '-I', '-S', *args)

    def test_returns_pid(self):
        pidfile = support.TESTFN
        self.addCleanup(support.unlink, pidfile)
        script = f"""if 1:
            import os
            with open({pidfile!r}, "w") as pidfile:
                pidfile.write(str(os.getpid()))
            """
        args = self.python_args('-c', script)
        pid = posix.posix_spawn(args[0], args, os.environ)
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        with open(pidfile) as f:
            self.assertEqual(f.read(), str(pid))

    def test_no_such_executable(self):
        no_such_executable = 'no_such_executable'
        try:
            pid = posix.posix_spawn(no_such_executable,
                                    [no_such_executable],
                                    os.environ)
        except FileNotFoundError as exc:
            self.assertEqual(exc.filename, no_such_executable)
        else:
            pid2, status = os.waitpid(pid, 0)
            self.assertEqual(pid2, pid)
            self.assertNotEqual(status, 0)

    def test_specify_environment(self):
        envfile = support.TESTFN
        self.addCleanup(support.unlink, envfile)
        script = f"""if 1:
            import os
            with open({envfile!r}, "w") as envfile:
                envfile.write(os.environ['foo'])
        """
        args = self.python_args('-c', script)
        pid = posix.posix_spawn(args[0], args,
                                {**os.environ, 'foo': 'bar'})
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        with open(envfile) as f:
            self.assertEqual(f.read(), 'bar')

    def test_empty_file_actions(self):
        pid = posix.posix_spawn(
            self.NOOP_PROGRAM[0],
            self.NOOP_PROGRAM,
            os.environ,
            file_actions=[]
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_resetids_explicit_default(self):
        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', 'pass'],
            os.environ,
            resetids=False
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_resetids(self):
        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', 'pass'],
            os.environ,
            resetids=True
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_resetids_wrong_type(self):
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, resetids=None)

    def test_setpgroup(self):
        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', 'pass'],
            os.environ,
            setpgroup=os.getpgrp()
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_setpgroup_wrong_type(self):
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setpgroup="023")

    @unittest.skipUnless(hasattr(signal, 'pthread_sigmask'),
                           'need signal.pthread_sigmask()')
    def test_setsigmask(self):
        code = textwrap.dedent("""\
            import _testcapi, signal
            _testcapi.raise_signal(signal.SIGUSR1)""")

        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', code],
            os.environ,
            setsigmask=[signal.SIGUSR1]
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_setsigmask_wrong_type(self):
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigmask=34)
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigmask=["j"])
        with self.assertRaises(ValueError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigmask=[signal.NSIG,
                                                      signal.NSIG+1])

    @unittest.skipUnless(hasattr(signal, 'pthread_sigmask'),
                         'need signal.pthread_sigmask()')
    def test_setsigdef(self):
        original_handler = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        code = textwrap.dedent("""\
            import _testcapi, signal
            _testcapi.raise_signal(signal.SIGUSR1)""")
        try:
            pid = posix.posix_spawn(
                sys.executable,
                [sys.executable, '-c', code],
                os.environ,
                setsigdef=[signal.SIGUSR1]
            )
        finally:
            signal.signal(signal.SIGUSR1, original_handler)

        pid2, status = os.waitpid(pid, 0)
        self.assertEqual(pid2, pid)
        self.assertTrue(os.WIFSIGNALED(status), status)
        self.assertEqual(os.WTERMSIG(status), signal.SIGUSR1)

    def test_setsigdef_wrong_type(self):
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigdef=34)
        with self.assertRaises(TypeError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigdef=["j"])
        with self.assertRaises(ValueError):
            posix.posix_spawn(sys.executable,
                              [sys.executable, "-c", "pass"],
                              os.environ, setsigdef=[signal.NSIG, signal.NSIG+1])

    @requires_sched
    def test_setscheduler_only_param(self):
        policy = os.sched_getscheduler(0)
        priority = os.sched_get_priority_min(policy)
        code = textwrap.dedent(f"""\
            import os
            if os.sched_getscheduler(0) != {policy}:
                os.exit(101)
            if os.sched_getparam(0).sched_priority != {priority}:
                os.exit(102)""")
        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', code],
            os.environ,
            scheduler=(None, os.sched_param(priority))
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    @requires_sched
    def test_setscheduler_with_policy(self):
        policy = os.sched_getscheduler(0)
        priority = os.sched_get_priority_min(policy)
        code = textwrap.dedent(f"""\
            import os
            if os.sched_getscheduler(0) != {policy}:
                os.exit(101)
            if os.sched_getparam(0).sched_priority != {priority}:
                os.exit(102)""")
        pid = posix.posix_spawn(
            sys.executable,
            [sys.executable, '-c', code],
            os.environ,
            scheduler=(policy, os.sched_param(priority))
        )
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_multiple_file_actions(self):
        file_actions = [
            (os.POSIX_SPAWN_OPEN, 3, os.path.realpath(__file__), os.O_RDONLY, 0),
            (os.POSIX_SPAWN_CLOSE, 0),
            (os.POSIX_SPAWN_DUP2, 1, 4),
        ]
        pid = posix.posix_spawn(self.NOOP_PROGRAM[0],
                                self.NOOP_PROGRAM,
                                os.environ,
                                file_actions=file_actions)
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))

    def test_bad_file_actions(self):
        args = self.NOOP_PROGRAM
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[None])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[()])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(None,)])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(12345,)])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(os.POSIX_SPAWN_CLOSE,)])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(os.POSIX_SPAWN_CLOSE, 1, 2)])
        with self.assertRaises(TypeError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(os.POSIX_SPAWN_CLOSE, None)])
        with self.assertRaises(ValueError):
            posix.posix_spawn(args[0], args, os.environ,
                              file_actions=[(os.POSIX_SPAWN_OPEN,
                                             3, __file__ + '\0',
                                             os.O_RDONLY, 0)])

    def test_open_file(self):
        outfile = support.TESTFN
        self.addCleanup(support.unlink, outfile)
        script = """if 1:
            import sys
            sys.stdout.write("hello")
            """
        file_actions = [
            (os.POSIX_SPAWN_OPEN, 1, outfile,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                stat.S_IRUSR | stat.S_IWUSR),
        ]
        args = self.python_args('-c', script)
        pid = posix.posix_spawn(args[0], args, os.environ,
                                file_actions=file_actions)
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        with open(outfile) as f:
            self.assertEqual(f.read(), 'hello')

    def test_close_file(self):
        closefile = support.TESTFN
        self.addCleanup(support.unlink, closefile)
        script = f"""if 1:
            import os
            try:
                os.fstat(0)
            except OSError as e:
                with open({closefile!r}, 'w') as closefile:
                    closefile.write('is closed %d' % e.errno)
            """
        args = self.python_args('-c', script)
        pid = posix.posix_spawn(args[0], args, os.environ,
                                file_actions=[(os.POSIX_SPAWN_CLOSE, 0),])
        self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        with open(closefile) as f:
            self.assertEqual(f.read(), 'is closed %d' % errno.EBADF)

    def test_dup2(self):
        dupfile = support.TESTFN
        self.addCleanup(support.unlink, dupfile)
        script = """if 1:
            import sys
            sys.stdout.write("hello")
            """
        with open(dupfile, "wb") as childfile:
            file_actions = [
                (os.POSIX_SPAWN_DUP2, childfile.fileno(), 1),
            ]
            args = self.python_args('-c', script)
            pid = posix.posix_spawn(args[0], args, os.environ,
                                    file_actions=file_actions)
            self.assertEqual(os.waitpid(pid, 0), (pid, 0))
        with open(dupfile) as f:
            self.assertEqual(f.read(), 'hello')


def test_main():
    try:
        support.run_unittest(PosixTester, PosixGroupsTester, TestPosixSpawn)
    finally:
        support.reap_children()

if __name__ == '__main__':
    test_main()
