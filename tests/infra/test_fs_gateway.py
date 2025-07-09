import pytest
from pathlib import Path
import tempfile
import json
import os
import stat
from unittest.mock import patch, Mock

from src.infra.fs_gateway import FSGateway, FSPermissionError


class TestFSGateway:
    """Test suite for FSGateway."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def fs_gateway(self):
        """Create a basic FSGateway instance."""
        return FSGateway()
    
    @pytest.fixture
    def restricted_gateway(self, temp_dir):
        """Create FSGateway restricted to temp directory."""
        return FSGateway(allowed_paths=[temp_dir])
    
    @pytest.fixture
    def readonly_gateway(self):
        """Create read-only FSGateway."""
        return FSGateway(read_only=True)
    
    def test_init_default(self):
        """Test FSGateway initialization with defaults."""
        gateway = FSGateway()
        assert gateway.allowed_paths == []
        assert gateway.read_only is False
    
    def test_init_with_allowed_paths(self, temp_dir):
        """Test FSGateway with allowed paths."""
        gateway = FSGateway(allowed_paths=[temp_dir, '/tmp'])
        assert len(gateway.allowed_paths) == 2
        assert all(isinstance(p, Path) for p in gateway.allowed_paths)
    
    def test_init_readonly(self):
        """Test FSGateway in read-only mode."""
        gateway = FSGateway(read_only=True)
        assert gateway.read_only is True
    
    def test_validate_path_allowed(self, restricted_gateway, temp_dir):
        """Test path validation within allowed paths."""
        test_path = temp_dir / 'test.txt'
        validated = restricted_gateway._validate_path(test_path)
        assert validated == test_path.resolve()
    
    def test_validate_path_denied(self, restricted_gateway):
        """Test path validation outside allowed paths."""
        with pytest.raises(FSPermissionError, match="outside allowed directories"):
            restricted_gateway._validate_path('/etc/passwd')
    
    def test_is_subpath(self, fs_gateway):
        """Test subpath checking."""
        parent = Path('/home/user')
        child = Path('/home/user/documents')
        not_child = Path('/etc')
        
        assert fs_gateway._is_subpath(child, parent) is True
        assert fs_gateway._is_subpath(not_child, parent) is False
    
    def test_check_write_permission_allowed(self, fs_gateway):
        """Test write permission check when allowed."""
        # Should not raise
        fs_gateway._check_write_permission()
    
    def test_check_write_permission_denied(self, readonly_gateway):
        """Test write permission check when read-only."""
        with pytest.raises(FSPermissionError, match="not permitted in read-only mode"):
            readonly_gateway._check_write_permission()
    
    def test_exists_file(self, fs_gateway, temp_dir):
        """Test checking if file exists."""
        test_file = temp_dir / 'exists.txt'
        test_file.write_text('content')
        
        assert fs_gateway.exists(test_file) is True
        assert fs_gateway.exists(temp_dir / 'nonexistent.txt') is False
    
    def test_exists_directory(self, fs_gateway, temp_dir):
        """Test checking if directory exists."""
        assert fs_gateway.exists(temp_dir) is True
        assert fs_gateway.exists(temp_dir / 'nonexistent') is False
    
    def test_is_file(self, fs_gateway, temp_dir):
        """Test checking if path is a file."""
        test_file = temp_dir / 'file.txt'
        test_file.write_text('content')
        
        assert fs_gateway.is_file(test_file) is True
        assert fs_gateway.is_file(temp_dir) is False
        assert fs_gateway.is_file(temp_dir / 'nonexistent') is False
    
    def test_is_dir(self, fs_gateway, temp_dir):
        """Test checking if path is a directory."""
        test_subdir = temp_dir / 'subdir'
        test_subdir.mkdir()
        
        assert fs_gateway.is_dir(temp_dir) is True
        assert fs_gateway.is_dir(test_subdir) is True
        assert fs_gateway.is_dir(temp_dir / 'file.txt') is False
    
    def test_read_text(self, fs_gateway, temp_dir):
        """Test reading text from file."""
        test_file = temp_dir / 'read.txt'
        test_file.write_text('Hello, World!')
        
        content = fs_gateway.read_text(test_file)
        assert content == 'Hello, World!'
    
    def test_read_text_encoding(self, fs_gateway, temp_dir):
        """Test reading text with specific encoding."""
        test_file = temp_dir / 'utf8.txt'
        test_file.write_text('Hello, 世界!', encoding='utf-8')
        
        content = fs_gateway.read_text(test_file, encoding='utf-8')
        assert content == 'Hello, 世界!'
    
    def test_read_text_nonexistent(self, fs_gateway, temp_dir):
        """Test reading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            fs_gateway.read_text(temp_dir / 'nonexistent.txt')
    
    def test_read_bytes(self, fs_gateway, temp_dir):
        """Test reading binary data from file."""
        test_file = temp_dir / 'binary.bin'
        test_data = b'\x00\x01\x02\x03'
        test_file.write_bytes(test_data)
        
        content = fs_gateway.read_bytes(test_file)
        assert content == test_data
    
    def test_write_text_atomic(self, fs_gateway, temp_dir):
        """Test atomic text writing."""
        test_file = temp_dir / 'write.txt'
        fs_gateway.write_text(test_file, 'Test content', atomic=True)
        
        assert test_file.exists()
        assert test_file.read_text() == 'Test content'
    
    def test_write_text_non_atomic(self, fs_gateway, temp_dir):
        """Test non-atomic text writing."""
        test_file = temp_dir / 'write.txt'
        fs_gateway.write_text(test_file, 'Test content', atomic=False)
        
        assert test_file.exists()
        assert test_file.read_text() == 'Test content'
    
    def test_write_text_readonly(self, readonly_gateway, temp_dir):
        """Test write fails in read-only mode."""
        with pytest.raises(FSPermissionError):
            readonly_gateway.write_text(temp_dir / 'test.txt', 'content')
    
    def test_write_bytes_atomic(self, fs_gateway, temp_dir):
        """Test atomic binary writing."""
        test_file = temp_dir / 'binary.bin'
        test_data = b'\x00\x01\x02\x03'
        fs_gateway.write_bytes(test_file, test_data, atomic=True)
        
        assert test_file.exists()
        assert test_file.read_bytes() == test_data
    
    def test_delete_file(self, fs_gateway, temp_dir):
        """Test file deletion."""
        test_file = temp_dir / 'delete.txt'
        test_file.write_text('content')
        
        fs_gateway.delete(test_file)
        assert not test_file.exists()
    
    def test_delete_missing_file(self, fs_gateway, temp_dir):
        """Test deleting missing file."""
        # Should raise by default
        with pytest.raises(FileNotFoundError):
            fs_gateway.delete(temp_dir / 'nonexistent.txt')
        
        # Should not raise with missing_ok=True
        fs_gateway.delete(temp_dir / 'nonexistent.txt', missing_ok=True)
    
    def test_delete_directory_error(self, fs_gateway, temp_dir):
        """Test delete raises error for directories."""
        with pytest.raises(IsADirectoryError):
            fs_gateway.delete(temp_dir)
    
    def test_mkdir_simple(self, fs_gateway, temp_dir):
        """Test simple directory creation."""
        new_dir = temp_dir / 'newdir'
        fs_gateway.mkdir(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_mkdir_parents(self, fs_gateway, temp_dir):
        """Test directory creation with parents."""
        new_dir = temp_dir / 'parent' / 'child' / 'grandchild'
        fs_gateway.mkdir(new_dir, parents=True)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_mkdir_exist_ok(self, fs_gateway, temp_dir):
        """Test mkdir with existing directory."""
        # Should not raise with exist_ok=True
        fs_gateway.mkdir(temp_dir, exist_ok=True)
        
        # Should raise with exist_ok=False
        with pytest.raises(FileExistsError):
            fs_gateway.mkdir(temp_dir, exist_ok=False)
    
    def test_delete_dir_empty(self, fs_gateway, temp_dir):
        """Test deleting empty directory."""
        test_dir = temp_dir / 'empty'
        test_dir.mkdir()
        
        fs_gateway.delete_dir(test_dir)
        assert not test_dir.exists()
    
    def test_delete_dir_not_empty(self, fs_gateway, temp_dir):
        """Test deleting non-empty directory."""
        test_dir = temp_dir / 'nonempty'
        test_dir.mkdir()
        (test_dir / 'file.txt').write_text('content')
        
        # Should fail without recursive
        with pytest.raises(OSError):
            fs_gateway.delete_dir(test_dir, recursive=False)
        
        # Should succeed with recursive
        fs_gateway.delete_dir(test_dir, recursive=True)
        assert not test_dir.exists()
    
    def test_copy_file(self, fs_gateway, temp_dir):
        """Test file copying."""
        src = temp_dir / 'source.txt'
        dst = temp_dir / 'dest.txt'
        src.write_text('content')
        
        fs_gateway.copy(src, dst)
        
        assert dst.exists()
        assert dst.read_text() == 'content'
    
    @pytest.mark.skipif(os.name == 'nt', reason="Permission testing unreliable on Windows")
    def test_copy_preserve_metadata(self, fs_gateway, temp_dir):
        """Test copying with metadata preservation."""
        src = temp_dir / 'source.txt'
        dst = temp_dir / 'dest.txt'
        src.write_text('content')
        src.chmod(0o644)
        
        fs_gateway.copy(src, dst, preserve_metadata=True)
        
        assert dst.stat().st_mode == src.stat().st_mode
    
    def test_move_file(self, fs_gateway, temp_dir):
        """Test moving/renaming file."""
        src = temp_dir / 'source.txt'
        dst = temp_dir / 'dest.txt'
        src.write_text('content')
        
        fs_gateway.move(src, dst)
        
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == 'content'
    
    def test_list_dir_simple(self, fs_gateway, temp_dir):
        """Test listing directory contents."""
        # Create some files
        (temp_dir / 'file1.txt').write_text('1')
        (temp_dir / 'file2.txt').write_text('2')
        (temp_dir / 'subdir').mkdir()
        
        contents = fs_gateway.list_dir(temp_dir)
        names = [p.name for p in contents]
        
        assert 'file1.txt' in names
        assert 'file2.txt' in names
        assert 'subdir' in names
        assert len(contents) == 3
    
    def test_list_dir_pattern(self, fs_gateway, temp_dir):
        """Test listing directory with pattern."""
        # Create files
        (temp_dir / 'test1.txt').write_text('1')
        (temp_dir / 'test2.txt').write_text('2')
        (temp_dir / 'other.dat').write_text('3')
        
        txt_files = fs_gateway.list_dir(temp_dir, pattern='*.txt')
        names = [p.name for p in txt_files]
        
        assert 'test1.txt' in names
        assert 'test2.txt' in names
        assert 'other.dat' not in names
        assert len(txt_files) == 2
    
    def test_walk_directory(self, fs_gateway, temp_dir):
        """Test walking directory tree."""
        # Create directory structure
        (temp_dir / 'file1.txt').write_text('1')
        subdir = temp_dir / 'subdir'
        subdir.mkdir()
        (subdir / 'file2.txt').write_text('2')
        deep = subdir / 'deep'
        deep.mkdir()
        (deep / 'file3.txt').write_text('3')
        
        # Collect all walked paths
        walked = list(fs_gateway.walk(temp_dir))
        
        assert len(walked) == 3  # root, subdir, deep
        
        # Check root
        root_path, root_dirs, root_files = walked[0]
        # Compare resolved paths to handle symlinks
        assert root_path == temp_dir.resolve()
        assert 'subdir' in root_dirs
        assert 'file1.txt' in root_files
    
    def test_get_size(self, fs_gateway, temp_dir):
        """Test getting file size."""
        test_file = temp_dir / 'sized.txt'
        content = 'Hello, World!'
        test_file.write_text(content)
        
        size = fs_gateway.get_size(test_file)
        assert size == len(content)
    
    def test_get_metadata(self, fs_gateway, temp_dir):
        """Test getting file metadata."""
        test_file = temp_dir / 'meta.txt'
        test_file.write_text('content')
        
        metadata = fs_gateway.get_metadata(test_file)
        
        assert metadata['size'] == 7
        assert metadata['is_file'] is True
        assert metadata['is_dir'] is False
        assert 'mode' in metadata
        assert 'permissions' in metadata
        assert 'mtime' in metadata
    
    @pytest.mark.skipif(os.name == 'nt', reason="chmod testing unreliable on Windows")
    def test_chmod(self, fs_gateway, temp_dir):
        """Test changing file permissions."""
        test_file = temp_dir / 'chmod.txt'
        test_file.write_text('content')
        
        fs_gateway.chmod(test_file, 0o600)
        
        mode = test_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600
    
    def test_compute_hash_sha256(self, fs_gateway, temp_dir):
        """Test computing SHA256 hash."""
        test_file = temp_dir / 'hash.txt'
        test_file.write_text('Hello, World!')
        
        hash_value = fs_gateway.compute_hash(test_file)
        # Known SHA256 for "Hello, World!"
        expected = 'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        assert hash_value == expected
    
    def test_compute_hash_md5(self, fs_gateway, temp_dir):
        """Test computing MD5 hash."""
        test_file = temp_dir / 'hash.txt'
        test_file.write_text('Hello, World!')
        
        hash_value = fs_gateway.compute_hash(test_file, algorithm='md5')
        # Known MD5 for "Hello, World!"
        expected = '65a8e27d8879283831b664bd8b7f0ad4'
        assert hash_value == expected
    
    def test_read_json(self, fs_gateway, temp_dir):
        """Test reading JSON file."""
        test_file = temp_dir / 'data.json'
        data = {'name': 'test', 'value': 42, 'items': [1, 2, 3]}
        test_file.write_text(json.dumps(data))
        
        loaded = fs_gateway.read_json(test_file)
        assert loaded == data
    
    def test_write_json(self, fs_gateway, temp_dir):
        """Test writing JSON file."""
        test_file = temp_dir / 'output.json'
        data = {'name': 'test', 'value': 42, 'items': [1, 2, 3]}
        
        fs_gateway.write_json(test_file, data)
        
        assert test_file.exists()
        loaded = json.loads(test_file.read_text())
        assert loaded == data
    
    def test_temp_dir_unrestricted(self, fs_gateway):
        """Test creating temporary directory without restrictions."""
        with fs_gateway.temp_dir(prefix='test_') as tmpdir:
            tmpdir_path = Path(tmpdir)
            assert tmpdir_path.exists()
            assert tmpdir_path.is_dir()
            assert 'test_' in tmpdir_path.name
        
        # Directory should be cleaned up
        assert not tmpdir_path.exists()
    
    def test_temp_dir_restricted(self, temp_dir):
        """Test temporary directory within allowed paths."""
        gateway = FSGateway(allowed_paths=[temp_dir])
        
        with gateway.temp_dir() as tmpdir:
            tmpdir_path = Path(tmpdir)
            assert tmpdir_path.exists()
            # Should be within allowed path
            assert str(temp_dir) in str(tmpdir_path)
    
    def test_ensure_parent_dir(self, fs_gateway, temp_dir):
        """Test ensuring parent directory exists."""
        file_path = temp_dir / 'deep' / 'nested' / 'file.txt'
        
        fs_gateway.ensure_parent_dir(file_path)
        
        assert file_path.parent.exists()
        assert file_path.parent.is_dir()
    
    def test_backward_compatibility_read(self, fs_gateway, temp_dir):
        """Test backward compatibility read method."""
        test_file = temp_dir / 'compat.txt'
        test_file.write_text('compatibility content')
        
        content = fs_gateway.read(test_file)
        assert content == 'compatibility content'
    
    def test_restricted_path_operations(self, temp_dir):
        """Test operations with restricted paths."""
        allowed_dir = temp_dir / 'allowed'
        allowed_dir.mkdir()
        forbidden_dir = temp_dir / 'forbidden'
        forbidden_dir.mkdir()
        
        gateway = FSGateway(allowed_paths=[allowed_dir])
        
        # Operations within allowed path should work
        test_file = allowed_dir / 'test.txt'
        gateway.write_text(test_file, 'allowed')
        assert gateway.read_text(test_file) == 'allowed'
        
        # Operations outside allowed path should fail
        forbidden_file = forbidden_dir / 'test.txt'
        with pytest.raises(FSPermissionError):
            gateway.write_text(forbidden_file, 'forbidden')
    
    def test_walk_with_restricted_paths(self, temp_dir):
        """Test walk respects path restrictions."""
        # Create structure with allowed and forbidden areas
        allowed = temp_dir / 'allowed'
        allowed.mkdir()
        (allowed / 'file1.txt').write_text('1')
        
        forbidden = temp_dir / 'forbidden'
        forbidden.mkdir()
        (forbidden / 'file2.txt').write_text('2')
        
        # Create gateway with temp_dir and allowed as allowed paths
        gateway = FSGateway(allowed_paths=[temp_dir])
        
        # Walk from temp_dir should see both directories
        walked_paths = []
        for root, dirs, files in gateway.walk(temp_dir):
            walked_paths.append(root)
        
        # Should see the temp directory itself
        assert any(path == temp_dir.resolve() for path in walked_paths)
        
        # Now test with restricted gateway
        restricted_gateway = FSGateway(allowed_paths=[allowed])
        
        # Walking allowed directory should work
        allowed_paths = list(restricted_gateway.walk(allowed))
        assert len(allowed_paths) == 1
        assert allowed_paths[0][0] == allowed.resolve()
    
    def test_permission_checks_fail_gracefully(self, temp_dir):
        """Test that permission checks return False for denied paths."""
        forbidden = temp_dir / 'forbidden'
        forbidden.mkdir()
        (forbidden / 'test.txt').write_text('content')
        
        gateway = FSGateway(allowed_paths=[temp_dir / 'allowed'])  # Different path
        
        # These should return False for paths outside allowed directories
        assert gateway.exists(forbidden) is False
        assert gateway.is_file(forbidden / 'test.txt') is False
        assert gateway.is_dir(forbidden) is False
    
    def test_delete_dir_not_directory(self, fs_gateway, temp_dir):
        """Test delete_dir fails on non-directory."""
        test_file = temp_dir / 'notdir.txt'
        test_file.write_text('content')
        
        with pytest.raises(NotADirectoryError):
            fs_gateway.delete_dir(test_file)
    
    def test_list_dir_not_directory(self, fs_gateway, temp_dir):
        """Test list_dir fails on non-directory."""
        test_file = temp_dir / 'notdir.txt'
        test_file.write_text('content')
        
        with pytest.raises(NotADirectoryError):
            fs_gateway.list_dir(test_file)
    
    def test_copy_without_metadata(self, fs_gateway, temp_dir):
        """Test copying without preserving metadata."""
        src = temp_dir / 'source.txt'
        dst = temp_dir / 'dest.txt'
        src.write_text('content')
        
        fs_gateway.copy(src, dst, preserve_metadata=False)
        
        assert dst.exists()
        assert dst.read_text() == 'content'