import os
import tempfile
import pytest
from pkg_resources import resource_filename

import klibs
from klibs import KLDatabase as kldb
from klibs.KLRuntimeInfo import runtime_info_init

from conftest import _init_params_pytest


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

def generate_id_row(uid=1, gender="f", age=24, handedness="r"):
    # Generate participant data
    dat = {
        "userhash": uid,
        "gender": gender,
        "age": age,
        "handedness": handedness,
        "created": "now",
    }
    return dat

def generate_data_row(pid=1, block=1, trial=1):
    # Generate trial data
    dat = {
        "participant_id": pid,
        "block_num": block,
        "trial_num": trial,
    }
    return dat

def build_test_data():
    rows = [
        generate_id_row(uid="P01"),
        generate_id_row(uid="P02", gender="m"),
        generate_id_row(uid="P03", age=26),
    ]
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

    def test_tables(self, db):
        assert "participants" in db.tables
        assert "trials" in db.tables
        assert "session_info" in db.tables
        assert "export_history" in db.tables
        assert not "misc" in db.tables

    def test_get_columns(self, db):
        for col in ['id', 'created', 'age', 'gender']:
            assert col in db.get_columns('participants')
        assert 'participant_id' in db.get_columns('trials')
        assert 'os_version' in db.get_columns('session_info')
        # Test exception on non-existant table
        with pytest.raises(ValueError):
            db.get_columns('nope')

    def test_insert(self, db):
        last_row = db.last_row_id('participants')
        assert last_row == None
        data = generate_id_row()
        row_id = db.insert(data, table='participants')
        last_row = db.last_row_id('participants')
        assert last_row == 1
        assert last_row == row_id
        # Test exception on non-existant table
        with pytest.raises(ValueError):
            db.insert(data, table='nope')
        # Test coersion of values to correct column types
        data = generate_id_row(uid=2)
        data["age"] = "27"
        db.insert(data, table='participants')
        assert db.last_row_id('participants') == 2
        # Test handling of 'allow null' columns
        _init_params_pytest()
        data = runtime_info_init()
        db.insert(data, table='session_info')
        assert db.last_row_id('session_info') == 1
        # Test inserting multiple rows of data
        rows = [generate_data_row(trial=i+1) for i in range(3)]
        db.insert(rows, table='trials')
        assert db.last_row_id('trials') == 3
        retrieved = db.select('trials')
        assert len(retrieved) == 3
        # Test inserting an empty list of rows
        db.insert([], table='trials')
        assert db.last_row_id('trials') == 3
        # Test exception when unable to coerce value to column type
        data = generate_id_row(uid=3)
        data["age"] = "hello"
        with pytest.raises(ValueError):
            db.insert(data, table='participants')
        # Test exception on extra column
        data = generate_id_row(uid=3)
        data["extra"] = True
        with pytest.raises(ValueError):
            db.insert(data, table='participants')
        # Test exception on missing column
        data = generate_id_row(uid=3)
        del data["created"]
        with pytest.raises(ValueError):
            db.insert(data, table='participants')

    def test_flush(self, db):
        # Insert test data into the database
        data = build_test_data()
        for row in data:
            db.insert(row, table='participants')
        # Flush the database and make sure row ids are reset
        last_row = db.last_row_id('participants')
        assert last_row > 1
        db._flush()
        assert len(db.select('participants')) == 0
        db.insert(data[0], table='participants')
        assert db.last_row_id('participants') == 1
        
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

    def test_select(self, db):
        # Insert test data into the database
        data = build_test_data()
        for row in data:
            db.insert(row, table='participants')
        # Select all data from the table
        tmp = db.select('participants')
        assert len(tmp) == 3
        assert len(tmp[0]) == len(data[0].keys()) + 1
        # Select a subset of the data
        tmp = db.select('participants', where={'age': 24})
        assert len(tmp) == 2
        ids = [r[0] for r in tmp]
        assert 1 in ids and 2 in ids
        # Select a few columns from the data
        tmp = db.select('participants', columns=['age', 'gender'])
        assert len(tmp) == 3
        assert len(tmp[0]) == 2
        assert tmp[0][0] == 24
        assert tmp[1][1] == "m"
        # Test distinct selection
        tmp = db.select('participants', columns=['age'], distinct=True)
        assert len(tmp) == 2
        row_values = [r[0] for r in tmp]
        assert 24 in row_values
        assert 26 in row_values

    def test_delete(self, db):
        # Insert test data into the database
        data = build_test_data()
        for row in data:
            db.insert(row, table='participants')
        # Try deleting a single row
        assert db.delete('participants', where={'gender': "m"}) == 1
        assert len(db.select('participants')) == 2
        # Try deleting a row using multiple filter criteria
        assert db.delete('participants', where={'gender': "f", 'age': 26}) == 1
        assert len(db.select('participants')) == 1
        # Try deleting with filter criteria that don't match anything
        assert db.delete('participants', where={'age': 18}) == 0
        assert len(db.select('participants')) == 1
        # Try deleting multiple rows
        row = generate_id_row(gender="m")
        db.insert(row, table='participants')
        assert db.delete('participants', where={'age': 24}) == 2
        assert len(db.select('participants')) == 0


class TestDatabaseManager(object):

    def test_init(self, db_test_path):
        dat = kldb.DatabaseManager(db_test_path)
        assert "participants" in list(dat.table_schemas.keys())
        assert "age" in list(dat.table_schemas['participants'].keys())
        assert dat.table_schemas['participants']['age']['type'] == klibs.PY_INT
        dat.close()

    def test_init_multi_user(self, db_test_path):
        tmpdir = tempfile.gettempdir()
        localpath = os.path.join(tmpdir, "tmp_local.db")
        dat = kldb.DatabaseManager(db_test_path, localpath)
        assert os.path.exists(localpath)
        assert "participants" in list(dat.table_schemas.keys())
        assert "age" in list(dat.table_schemas['participants'].keys())
        assert dat.table_schemas['participants']['age']['type'] == klibs.PY_INT
        dat.close()

    def test_get_unique_ids(self, db_test_path):
        dat = kldb.DatabaseManager(db_test_path)
        # Add test data
        id_data = build_test_data()
        for row in id_data:
            dat.insert(row, table='participants')
        for pid in (1, 2, 3):
            dat.insert(generate_data_row(pid), table='trials')
            dat.insert(generate_data_row(pid, trial=2), table='trials')
            assert "P0{0}".format(pid) in dat.get_unique_ids()
        assert len(dat.get_unique_ids()) == 3
        assert not "P04" in dat.get_unique_ids()
        dat.close()

    def test_remove_data(self, db_test_path):
        dat = kldb.DatabaseManager(db_test_path)
        # Add test data
        id_data = build_test_data()
        for row in id_data:
            dat.insert(row, table='participants')
        for pid in (1, 2, 3):
            dat.insert(generate_data_row(pid), table='trials')
            dat.insert(generate_data_row(pid, trial=2), table='trials')
        # Try removing data for P02
        assert len(dat.select('participants', where={'userhash': "P02"})) == 1
        assert len(dat.select('trials', where={'participant_id': 2})) == 2
        dat.remove_data("P02")
        assert len(dat.select('participants', where={'userhash': "P02"})) == 0
        assert len(dat.select('trials', where={'participant_id': 2})) == 0
        assert len(dat.select('participants')) == 2
        assert len(dat.select('trials')) == 4
        # Test exception on invalid unique ID
        with pytest.raises(ValueError):
            dat.remove_data("P011001010101")
        dat.close()

    def test_num_data_rows(self, db_test_path):
        dat = kldb.DatabaseManager(db_test_path)
        # Add test data
        id_data = build_test_data()
        for row in id_data:
            dat.insert(row, table='participants')
        for pid in (1, 2, 3):
            dat.insert(generate_data_row(pid), table='trials')
            dat.insert(generate_data_row(pid, trial=2), table='trials')
        dat.insert(generate_data_row(1, trial=3), table='trials')
        # Try checking trial counts
        assert dat.num_data_rows("P01") == 3
        assert dat.num_data_rows("P02") == 2
        # Test exception on invalid unique ID
        with pytest.raises(ValueError):
            dat.remove_data("P011001010101")
        dat.close()
