// Cooperative-only same-file publication. Not a lock against uncoordinated writers.
import Foundation
import CryptoKit
import Darwin
let a = CommandLine.arguments
func finish(_ state: String) -> Never { print("{\"state\":\"" + state + "\"}"); exit(state == "synced" ? 0 : 1) }
guard (a.count == 6 || a.count == 7), let fd = Int32(a[2]) else { finish("invalid") }
let root = URL(fileURLWithPath: a[1]), target = root.appendingPathComponent(a[3])
var pinned = stat(), named = stat()
guard fstat(fd, &pinned) == 0, stat(a[1], &named) == 0,
      pinned.st_dev == named.st_dev, pinned.st_ino == named.st_ino else { finish("offline") }
var error: NSError?, outcome = "offline"
NSFileCoordinator().coordinate(writingItemAt: target, options: .forReplacing, error: &error) { url in
    do {
        let values = try url.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemDownloadingStatusKey, .ubiquitousItemHasUnresolvedConflictsKey])
        if values.ubiquitousItemHasUnresolvedConflicts == true || !(NSFileVersion.unresolvedConflictVersionsOfItem(at: url) ?? []).isEmpty { outcome = "conflict"; return }
        if values.isUbiquitousItem == true && values.ubiquitousItemDownloadingStatus != .current { outcome = "offline"; return }
        let source = openat(fd, a[3], O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard source >= 0 else { return }
        defer { close(source) }
        var info = stat()
        guard fstat(source, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG, info.st_nlink == 1, info.st_size <= 8388608 else { outcome = "unsafe"; return }
        let handle = FileHandle(fileDescriptor: source, closeOnDealloc: false)
        let bytes = try handle.readToEnd() ?? Data()
        let hash = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        guard hash == a[5] else { outcome = "changed"; return }
        if a[4] == "-" { outcome = "synced"; return }
        guard a.count == 7, let expires = Double(a[6]), ProcessInfo.processInfo.systemUptime < expires else { outcome = "expired"; return }
        // The caller staged and fsynced a create-exclusive file in the pinned root.
        guard renameat(fd, a[4], fd, a[3]) == 0, fsync(fd) == 0 else { return }
        outcome = "synced"
    } catch { outcome = "offline" }
}
finish(error == nil ? outcome : "offline")
