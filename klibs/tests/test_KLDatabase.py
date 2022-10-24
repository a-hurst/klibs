import os
import tempfile
import pytest
from pkg_resources import resource_filename

import klibs
from klibs import KLDatabase as kldb


schema_path = resource_filename('klibs', 'resources/template/schema.sql')

@pytest.fixture
def db_test_path():
    tmpdir = tempfile.gettempdir()
    testpath = os.path.join(tmpdir, "tmp.db")
    kldb.rebuild_database(testpath, schema_path)
    assert os.path.exists(testpath)
    yield testpath
    os.remove(testpath)

@pytest.fixture
def db(db_test_path):
    tmp = kldb.Database(db_test_path)
    yield tmp
    tmp.close()

def get_id_data():
    # Generate trial data
    dat = {
        "userhash": "1",
        "gender": "f",
        "age": 24,
        "handedness": "r",
        "created": "now"
    }
    return dat

def build_test_data():
    rows = []
    dat = get_id_data()
    rows.append(dat)
    dat = get_id_data()
    dat["gender"] = "m"
    rows.append(dat)
    dat = get_id_data()
    dat["age"] = 26
    rows.append(dat)
    return rows


def test_rebuild_database():
    tmpdir = tempfile.gettempdir()
    testpath = os.path.join(tmpdir, "test.db")
    # Test creating a database from the default schema
    kldb.rebuild_database(testpath, schema_path)
    assert os.path.exists(testpath)
    # Test that the old database gets backed up on rebuild
    kldb.rebuild_database(testpath, schema_path)
    assert os.path.exists(testpath + ".backup")



class TestDatabase(object):

    def test_init(self, db_test_path):
        dat = kldb.Database(db_test_path)
        assert "participants" in list(dat.table_schemas.keys())
        assert "age" in list(dat.table_schemas['participants'].keys())
        assert dat.table_schemas['participants']['age']['type'] == klibs.PY_INT
        dat.close()

    def test_insert(self, db):
        last_row = db.last_id_from('participants')
        assert last_row == None
        data = get_id_data()
        db.insert(data, table='participants')
        last_row = db.last_id_from('participants')
        assert last_row == 1
        
    def test_exists(self, db):
        # Insert test data into the database
        data = build_test_data()
        for row in data:
            db.insert(row, table='participants')
        # Query different aspects of the data
        assert db.exists('participants', 'age', 24)
        assert not db.exists('participants', 'age', 100)
        assert db.exists('participants', 'gender', 'm')
        assert not db.exists('participants', 'handedness', 'a')

    
