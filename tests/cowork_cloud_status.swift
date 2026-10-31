// Read provider metadata for one explicitly selected synthetic proof artifact.
import Foundation
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let values = try url.resourceValues(forKeys: [.isUbiquitousItemKey, .ubiquitousItemIsUploadedKey, .ubiquitousItemIsUploadingKey, .ubiquitousItemUploadingErrorKey, .ubiquitousItemHasUnresolvedConflictsKey])
let report: [String: Any] = ["ubiquitous": values.isUbiquitousItem ?? false,
 "uploaded": values.ubiquitousItemIsUploaded ?? false,
 "uploading": values.ubiquitousItemIsUploading ?? false,
 "unresolved_conflicts": values.ubiquitousItemHasUnresolvedConflicts ?? false,
 "upload_error": values.ubiquitousItemUploadingError == nil ? "none" : "provider-error",
 "receiving_device": "not tested"]
print(String(data: try JSONSerialization.data(withJSONObject: report, options: .sortedKeys), encoding: .utf8)!)
