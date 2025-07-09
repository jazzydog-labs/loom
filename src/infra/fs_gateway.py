"""FileSystem Gateway for safe file operations with permission handling."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Union, List, Optional, Dict, Any, Iterator
import stat
import json
import hashlib


class FSPermissionError(Exception):
    """Raised when a file operation is not permitted."""
    pass


class FSGateway:
    """Gateway for file system operations with safety checks and permission handling.
    
    This gateway provides a safe interface for file system operations with:
    - Path validation and normalization
    - Permission checking
    - Atomic write operations
    - Safe directory operations
    - File metadata handling
    """
    
    def __init__(self, allowed_paths: Optional[List[Union[str, Path]]] = None,
                 read_only: bool = False):
        """Initialize FSGateway with optional restrictions.
        
        Args:
            allowed_paths: List of paths where operations are allowed.
                          If None, operations are allowed anywhere.
            read_only: If True, only read operations are permitted.
        """
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
        self.read_only = read_only
    
    def _validate_path(self, path: Union[str, Path]) -> Path:
        """Validate and normalize a path.
        
        Args:
            path: Path to validate
            
        Returns:
            Normalized Path object
            
        Raises:
            FSPermissionError: If path is outside allowed paths
        """
        normalized = Path(path).resolve()
        
        # Check if path is within allowed paths
        if self.allowed_paths:
            if not any(self._is_subpath(normalized, allowed) 
                      for allowed in self.allowed_paths):
                raise FSPermissionError(
                    f"Path {path} is outside allowed directories"
                )
        
        return normalized
    
    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is a subpath of parent."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
    
    def _check_write_permission(self) -> None:
        """Check if write operations are allowed."""
        if self.read_only:
            raise FSPermissionError("Write operations not permitted in read-only mode")
    
    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists
        """
        try:
            normalized = self._validate_path(path)
            return normalized.exists()
        except FSPermissionError:
            return False
    
    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        try:
            normalized = self._validate_path(path)
            return normalized.is_file()
        except FSPermissionError:
            return False
    
    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        try:
            normalized = self._validate_path(path)
            return normalized.is_dir()
        except FSPermissionError:
            return False
    
    def read_text(self, path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """Read text from a file.
        
        Args:
            path: Path to read from
            encoding: Text encoding
            
        Returns:
            File contents as string
            
        Raises:
            FSPermissionError: If path is not allowed
            FileNotFoundError: If file doesn't exist
        """
        normalized = self._validate_path(path)
        return normalized.read_text(encoding=encoding)
    
    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read binary data from a file.
        
        Args:
            path: Path to read from
            
        Returns:
            File contents as bytes
        """
        normalized = self._validate_path(path)
        return normalized.read_bytes()
    
    def write_text(self, path: Union[str, Path], content: str, 
                   encoding: str = 'utf-8', atomic: bool = True) -> None:
        """Write text to a file.
        
        Args:
            path: Path to write to
            content: Text content to write
            encoding: Text encoding
            atomic: If True, write atomically using temp file
            
        Raises:
            FSPermissionError: If write not allowed
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        
        if atomic:
            # Write to temp file and move atomically
            with tempfile.NamedTemporaryFile(mode='w', encoding=encoding,
                                            dir=normalized.parent,
                                            delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            
            # Preserve permissions if file exists
            if normalized.exists():
                shutil.copystat(normalized, tmp_path)
            
            # Atomic rename
            tmp_path.replace(normalized)
        else:
            normalized.write_text(content, encoding=encoding)
    
    def write_bytes(self, path: Union[str, Path], content: bytes,
                    atomic: bool = True) -> None:
        """Write binary data to a file.
        
        Args:
            path: Path to write to
            content: Binary content to write
            atomic: If True, write atomically using temp file
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        
        if atomic:
            # Write to temp file and move atomically
            with tempfile.NamedTemporaryFile(mode='wb', dir=normalized.parent,
                                            delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            
            # Preserve permissions if file exists
            if normalized.exists():
                shutil.copystat(normalized, tmp_path)
            
            # Atomic rename
            tmp_path.replace(normalized)
        else:
            normalized.write_bytes(content)
    
    def delete(self, path: Union[str, Path], missing_ok: bool = False) -> None:
        """Delete a file.
        
        Args:
            path: Path to delete
            missing_ok: If True, don't raise error if file doesn't exist
            
        Raises:
            FSPermissionError: If delete not allowed
            FileNotFoundError: If file doesn't exist and missing_ok=False
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        
        if normalized.is_dir():
            raise IsADirectoryError(f"Use delete_dir() to delete directory: {path}")
        
        try:
            normalized.unlink()
        except FileNotFoundError:
            if not missing_ok:
                raise
    
    def mkdir(self, path: Union[str, Path], parents: bool = True,
              exist_ok: bool = True, mode: int = 0o755) -> None:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: If True, create parent directories as needed
            exist_ok: If True, don't raise error if directory exists
            mode: Directory permissions
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        normalized.mkdir(parents=parents, exist_ok=exist_ok, mode=mode)
    
    def delete_dir(self, path: Union[str, Path], recursive: bool = False) -> None:
        """Delete a directory.
        
        Args:
            path: Directory path to delete
            recursive: If True, delete directory and all contents
            
        Raises:
            FSPermissionError: If delete not allowed
            OSError: If directory not empty and recursive=False
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        
        if not normalized.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        if recursive:
            shutil.rmtree(normalized)
        else:
            normalized.rmdir()
    
    def copy(self, src: Union[str, Path], dst: Union[str, Path],
             preserve_metadata: bool = True) -> None:
        """Copy a file.
        
        Args:
            src: Source file path
            dst: Destination file path
            preserve_metadata: If True, preserve file metadata
        """
        self._check_write_permission()
        src_normalized = self._validate_path(src)
        dst_normalized = self._validate_path(dst)
        
        if preserve_metadata:
            shutil.copy2(src_normalized, dst_normalized)
        else:
            shutil.copy(src_normalized, dst_normalized)
    
    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file or directory.
        
        Args:
            src: Source path
            dst: Destination path
        """
        self._check_write_permission()
        src_normalized = self._validate_path(src)
        dst_normalized = self._validate_path(dst)
        shutil.move(str(src_normalized), str(dst_normalized))
    
    def list_dir(self, path: Union[str, Path], 
                 pattern: Optional[str] = None) -> List[Path]:
        """List directory contents.
        
        Args:
            path: Directory path
            pattern: Optional glob pattern to filter results
            
        Returns:
            List of paths in directory
        """
        normalized = self._validate_path(path)
        
        if not normalized.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        if pattern:
            return sorted(normalized.glob(pattern))
        else:
            return sorted(normalized.iterdir())
    
    def walk(self, path: Union[str, Path], 
             follow_symlinks: bool = False) -> Iterator[tuple]:
        """Walk directory tree.
        
        Args:
            path: Root directory path
            follow_symlinks: If True, follow symbolic links
            
        Yields:
            Tuples of (dirpath, dirnames, filenames)
        """
        normalized = self._validate_path(path)
        
        for root, dirs, files in os.walk(normalized, followlinks=follow_symlinks):
            # Validate each directory in the walk
            try:
                self._validate_path(root)
                yield (Path(root), dirs, files)
            except FSPermissionError:
                # Skip directories outside allowed paths
                dirs.clear()  # Don't descend into subdirectories
    
    def get_size(self, path: Union[str, Path]) -> int:
        """Get file size in bytes.
        
        Args:
            path: File path
            
        Returns:
            File size in bytes
        """
        normalized = self._validate_path(path)
        return normalized.stat().st_size
    
    def get_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Get file metadata.
        
        Args:
            path: File path
            
        Returns:
            Dictionary with metadata including size, timestamps, permissions
        """
        normalized = self._validate_path(path)
        stat_info = normalized.stat()
        
        return {
            'size': stat_info.st_size,
            'mode': oct(stat_info.st_mode),
            'permissions': stat.filemode(stat_info.st_mode),
            'uid': stat_info.st_uid,
            'gid': stat_info.st_gid,
            'atime': stat_info.st_atime,
            'mtime': stat_info.st_mtime,
            'ctime': stat_info.st_ctime,
            'is_file': normalized.is_file(),
            'is_dir': normalized.is_dir(),
            'is_symlink': normalized.is_symlink()
        }
    
    def chmod(self, path: Union[str, Path], mode: int) -> None:
        """Change file permissions.
        
        Args:
            path: File path
            mode: New permissions (e.g., 0o755)
        """
        self._check_write_permission()
        normalized = self._validate_path(path)
        normalized.chmod(mode)
    
    def compute_hash(self, path: Union[str, Path], 
                     algorithm: str = 'sha256') -> str:
        """Compute hash of file contents.
        
        Args:
            path: File path
            algorithm: Hash algorithm (sha256, md5, etc.)
            
        Returns:
            Hex digest of file hash
        """
        normalized = self._validate_path(path)
        hasher = hashlib.new(algorithm)
        
        with normalized.open('rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def read_json(self, path: Union[str, Path]) -> Any:
        """Read and parse JSON file.
        
        Args:
            path: JSON file path
            
        Returns:
            Parsed JSON data
        """
        content = self.read_text(path)
        return json.loads(content)
    
    def write_json(self, path: Union[str, Path], data: Any,
                   indent: int = 2, atomic: bool = True) -> None:
        """Write data as JSON to file.
        
        Args:
            path: File path
            data: Data to serialize as JSON
            indent: JSON indentation
            atomic: If True, write atomically
        """
        content = json.dumps(data, indent=indent)
        self.write_text(path, content, atomic=atomic)
    
    def temp_dir(self, prefix: str = 'fsgateway_',
                 cleanup: bool = True) -> tempfile.TemporaryDirectory:
        """Create a temporary directory.
        
        Args:
            prefix: Directory name prefix
            cleanup: If True, directory is deleted when context exits
            
        Returns:
            TemporaryDirectory context manager
        """
        # If we have allowed paths, create temp dir within first allowed path
        if self.allowed_paths:
            temp_root = self.allowed_paths[0]
        else:
            temp_root = None
        
        return tempfile.TemporaryDirectory(prefix=prefix, dir=temp_root)
    
    def ensure_parent_dir(self, path: Union[str, Path]) -> None:
        """Ensure parent directory exists for a file path.
        
        Args:
            path: File path whose parent directory should be created
        """
        normalized = self._validate_path(path)
        self.mkdir(normalized.parent, parents=True, exist_ok=True)
    
    # Backward compatibility method
    def read(self, path):
        """Read text from a file (backward compatibility)."""
        return self.read_text(path)