import errno
from pyroute2.ipset import IPSet
from pyroute2.netlink.exceptions import NetlinkError
from utils import require_user
from uuid import uuid4


class TestIPSet(object):

    def setup(self):
        self.ip = IPSet()

    def teardown(self):
        self.ip.close()

    def list_ipset(self, name):
        try:
            res = {}
            msg_list = self.ip.list(name)
            adt = 'IPSET_ATTR_ADT'
            proto = 'IPSET_ATTR_PROTO'
            ipaddr = 'IPSET_ATTR_IPADDR_IPV4'
            for msg in msg_list:
                for x in msg.get_attr(adt).get_attrs(proto):
                    ip = x.get_attr('IPSET_ATTR_IP_FROM').get_attr(ipaddr)
                    res[ip] = (x.get_attr("IPSET_ATTR_PACKETS"),
                               x.get_attr("IPSET_ATTR_BYTES"),
                               x.get_attr("IPSET_ATTR_COMMENT"))
            return res
        except:
            return {}

    def get_ipset(self, name):
        return [x for x in self.ip.list()
                if x.get_attr('IPSET_ATTR_SETNAME') == name]

    def test_create_exclusive_fail(self):
        require_user('root')
        name = str(uuid4())[:16]
        self.ip.create(name)
        assert self.get_ipset(name)
        try:
            self.ip.create(name)
        except NetlinkError as e:
            if e.code != errno.EEXIST:  # File exists
                raise
        finally:
            self.ip.destroy(name)
        assert not self.get_ipset(name)

    def test_create_exclusive_success(self):
        require_user('root')
        name = str(uuid4())[:16]
        self.ip.create(name)
        assert self.get_ipset(name)
        self.ip.create(name, exclusive=False)
        self.ip.destroy(name)
        assert not self.get_ipset(name)

    def test_add_exclusive_fail(self):
        require_user('root')
        name = str(uuid4())[:16]
        ipaddr = '172.16.202.202'
        self.ip.create(name)
        self.ip.add(name, ipaddr)
        assert ipaddr in self.list_ipset(name)
        try:
            self.ip.add(name, ipaddr)
        except NetlinkError:
            pass
        finally:
            self.ip.destroy(name)
        assert not self.get_ipset(name)

    def test_add_exclusive_success(self):
        require_user('root')
        name = str(uuid4())[:16]
        ipaddr = '172.16.202.202'
        self.ip.create(name)
        self.ip.add(name, ipaddr)
        assert ipaddr in self.list_ipset(name)
        self.ip.add(name, ipaddr, exclusive=False)
        self.ip.destroy(name)
        assert not self.get_ipset(name)

    def test_create_destroy(self):
        require_user('root')
        name = str(uuid4())[:16]
        # create ipset
        self.ip.create(name)
        # assert it exists
        assert self.get_ipset(name)
        # remove ipset
        self.ip.destroy(name)
        # assert it is removed
        assert not self.get_ipset(name)

    def test_add_delete(self):
        require_user('root')
        name = str(uuid4())[:16]
        ipaddr = '192.168.1.1'
        # create ipset
        self.ip.create(name)
        assert self.get_ipset(name)
        # add an entry
        self.ip.add(name, ipaddr)
        # check it
        assert ipaddr in self.list_ipset(name)
        # delete an entry
        self.ip.delete(name, ipaddr)
        # check it
        assert ipaddr not in self.list_ipset(name)
        # remove ipset
        self.ip.destroy(name)
        assert not self.get_ipset(name)

    def test_swap(self):
        require_user('root')
        name_a = str(uuid4())[:16]
        name_b = str(uuid4())[:16]
        ipaddr_a = '192.168.1.1'
        ipaddr_b = '10.0.0.1'

        # create sets
        self.ip.create(name_a)
        self.ip.create(name_b)
        # add ips
        self.ip.add(name_a, ipaddr_a)
        self.ip.add(name_b, ipaddr_b)
        assert ipaddr_a in self.list_ipset(name_a)
        assert ipaddr_b in self.list_ipset(name_b)
        # swap sets
        self.ip.swap(name_a, name_b)
        assert ipaddr_a in self.list_ipset(name_b)
        assert ipaddr_b in self.list_ipset(name_a)
        # remove sets
        self.ip.destroy(name_a)
        self.ip.destroy(name_b)
        assert not self.get_ipset(name_a)
        assert not self.get_ipset(name_b)

    def test_counters(self):
        require_user('root')
        name = str(uuid4())[:16]
        ipaddr = '172.16.202.202'
        self.ip.create(name, counters=True)
        self.ip.add(name, ipaddr)
        assert ipaddr in self.list_ipset(name)
        assert self.list_ipset(name)[ipaddr][0] == 0  # Bytes
        assert self.list_ipset(name)[ipaddr][1] == 0  # Packets
        self.ip.destroy(name)

        self.ip.create(name, counters=False)
        self.ip.add(name, ipaddr)
        assert ipaddr in self.list_ipset(name)
        assert self.list_ipset(name)[ipaddr][0] is None
        assert self.list_ipset(name)[ipaddr][1] is None
        self.ip.destroy(name)

    def test_comments(self):
        require_user('root')
        name = str(uuid4())[:16]
        ipaddr = '172.16.202.202'
        comment = 'a very simple comment'
        self.ip.create(name, comment=True)
        self.ip.add(name, ipaddr, comment=comment)
        assert ipaddr in self.list_ipset(name)
        assert self.list_ipset(name)[ipaddr][2] == comment
        self.ip.destroy(name)

    def test_maxelem(self):
        require_user('root')
        name = str(uuid4())[:16]
        self.ip.create(name, maxelem=1)
        data = self.get_ipset(name)[0].get_attr("IPSET_ATTR_DATA")
        maxelem = data.get_attr("IPSET_ATTR_MAXELEM")
        self.ip.destroy(name)
        assert maxelem == 1

    def test_hashsize(self):
        require_user('root')
        name = str(uuid4())[:16]
        min_size = 64
        self.ip.create(name, hashsize=min_size)
        data = self.get_ipset(name)[0].get_attr("IPSET_ATTR_DATA")
        hashsize = data.get_attr("IPSET_ATTR_HASHSIZE")
        self.ip.destroy(name)
        assert hashsize == min_size

    def test_forceadd(self):
        require_user('root')
        name = str(uuid4())[:16]
        # The forceadd option only works when the entry that we try to add
        # share the same hash in the kernel hashtable than an entry already in
        # the IPSet. That is not so easy to test: we must create collisions
        # We achieve this goal with a very short hashsize (the kernel minimum)
        # and many entries.
        maxelem = 16384
        ipaddr = "172.16.202.202"
        self.ip.create(name, maxelem=maxelem, hashsize=64)

        def fill_to_max_entries(name):
            ip_start = "10.10.%d.%d"
            for i in range(0, maxelem):
                self.ip.add(name, ip_start % (i / 255, i % 255))

        fill_to_max_entries(name)
        try:
            self.ip.add(name, ipaddr)
            assert False
        except NetlinkError:
            pass
        finally:
            assert ipaddr not in self.list_ipset(name)
            self.ip.destroy(name)

        self.ip.create(name, hashsize=64, maxelem=maxelem, forceadd=True)
        fill_to_max_entries(name)
        self.ip.add(name, ipaddr)

        assert ipaddr in self.list_ipset(name)
        self.ip.destroy(name)

    def test_flush(self):
        require_user('root')
        name = str(uuid4())[:16]
        self.ip.create(name)
        ip_a = "1.1.1.1"
        ip_b = "1.2.3.4"
        self.ip.add(name, ip_a)
        self.ip.add(name, ip_b)
        assert ip_a in self.list_ipset(name)
        assert ip_b in self.list_ipset(name)
        self.ip.flush(name)
        assert ip_a not in self.list_ipset(name)
        assert ip_b not in self.list_ipset(name)
        self.ip.destroy(name)
