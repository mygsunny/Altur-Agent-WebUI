// Native safety qualification, NOT a document publisher.
// Only creates a fresh UUID directory beneath an explicitly supplied test parent.
import Foundation
import Darwin

let parent = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let fm = FileManager.default
let root = parent.appendingPathComponent("cowork-coordination-proof-" + UUID().uuidString, isDirectory: true)
try fm.createDirectory(at: root, withIntermediateDirectories: false)
let target = root.appendingPathComponent("synthetic.bin")
let backup = root.appendingPathComponent("baseline.backup")
let baseline = Data("synthetic-baseline".utf8)
let external = Data("synthetic-external-save".utf8)
let editor = Data("synthetic-editor-save".utf8)
try baseline.write(to: target, options: .withoutOverwriting)
var coordinationError: NSError?
var accessorError: Error?
var entered = false
NSFileCoordinator(filePresenter: nil).coordinate(writingItemAt: target, options: .forReplacing, error: &coordinationError) { url in
    do {
        entered = true
        let checked = try Data(contentsOf: url)
        precondition(checked == baseline)
        try checked.write(to: backup, options: .withoutOverwriting)
        // Independent process uses a normal atomic save, without coordination.
        // Schedule it AFTER the final read/backup and BEFORE replacement.
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = ["-c", "import os,sys; p=sys.argv[1]; q=p+'.external'; open(q,'xb').write(b'synthetic-external-save'); os.replace(q,p)", url.path]
        try process.run()
        process.waitUntilExit()
        precondition(process.terminationStatus == 0)
        let raced = try Data(contentsOf: url)
        precondition(raced == external)
        try editor.write(to: url, options: .atomic)
    } catch { accessorError = error }
}
if let error = coordinationError { throw error }
if let error = accessorError { throw error }
precondition(entered)
let final = try Data(contentsOf: target)
let savedBackup = try Data(contentsOf: backup)
precondition(final == editor && savedBackup == baseline)
let preservedExternal = final == external || savedBackup == external
let report: [String: Any] = [
    "coordinated_accessor_entered": entered,
    "external_process_completed_inside_accessor": true,
    "external_bytes_preserved": preservedExternal,
    "baseline_backup_preserved": savedBackup == baseline,
    "qualification": preservedExternal ? "unexpected-preservation" : "unsafe-noncooperative-overwrite-demonstrated",
    "proof_directory": root.path
]
let json = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
print(String(data: json, encoding: .utf8)!)
// Leave exact synthetic artifacts for inspection; never touch existing documents.
