import unittest

from backend.services.mount_utils import is_cifs_mounted, mount_fstype


class TestMountUtils(unittest.TestCase):
    def test_mount_fstype_returns_longest_matching_mount(self):
        mounts = (
            "overlay / overlay rw,relatime 0 0\n"
            "//192.168.1.2/share /mnt cifs rw,relatime 0 0\n"
            "//192.168.1.2/share/replica /mnt/replica cifs rw,relatime 0 0\n"
        )
        self.assertEqual(mount_fstype("/mnt/replica", mounts_text=mounts), "cifs")
        self.assertEqual(mount_fstype("/mnt/replica/RagflowAuth", mounts_text=mounts), "cifs")

    def test_mount_fstype_returns_none_when_missing(self):
        mounts = "overlay / overlay rw,relatime 0 0\n"
        self.assertIsNone(mount_fstype("/mnt/replica", mounts_text=mounts))

    def test_is_cifs_mounted(self):
        mounts = "//192.168.1.2/share /mnt/replica cifs rw,relatime 0 0\n"
        self.assertTrue(is_cifs_mounted("/mnt/replica", mounts_text=mounts))
        self.assertFalse(is_cifs_mounted("/mnt/not-replica", mounts_text=mounts))

