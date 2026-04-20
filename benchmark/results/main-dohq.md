# Artifactory benchmark results: main-dohq

| label | operation | size | num_workers | extra | runs | median(s) | stdev(s) | min(s) | max(s) |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| main-dohq | put_file | 1KB | 1 |  | 5 | 0.2541 | 0.0432 | 0.2489 | 0.3499 |
| main-dohq | put_file | 1MB | 1 |  | 5 | 0.3148 | 0.0901 | 0.2971 | 0.5127 |
| main-dohq | put_file | 50MB | 1 |  | 5 | 1.2012 | 0.4598 | 1.07 | 2.1889 |
| main-dohq | get_file | 1KB | 1 |  | 5 | 0.0785 | 0.0218 | 0.0778 | 0.1284 |
| main-dohq | get_file | 1KB | 6 |  | 5 | 0.082 | 0.0053 | 0.0782 | 0.0907 |
| main-dohq | get_file | 1MB | 1 |  | 5 | 0.1364 | 0.0987 | 0.1233 | 0.3555 |
| main-dohq | get_file | 1MB | 6 |  | 5 | 0.1328 | 0.0038 | 0.1255 | 0.1357 |
| main-dohq | get_file | 50MB | 1 |  | 5 | 0.6343 | 0.0433 | 0.6329 | 0.7304 |
| main-dohq | get_file | 50MB | 6 |  | 5 | 0.6324 | 0.0039 | 0.631 | 0.6393 |
| main-dohq | exists | 1KB | 1 |  | 5 | 0.0392 | 0.0009 | 0.0388 | 0.0407 |
| main-dohq | checksum | 1KB | 1 |  | 5 | 0.0394 | 0.003 | 0.0379 | 0.0455 |
| main-dohq | date | 1KB | 1 |  | 5 | 0.042 | 0.0007 | 0.0414 | 0.0433 |
| main-dohq | owner | 1KB | 1 |  | 5 | 0.042 | 0.0016 | 0.0393 | 0.0429 |
| main-dohq | ls | - | 1 | 10_files | 5 | 1.0099 | 0.0993 | 0.9753 | 1.196 |
| main-dohq | ls | - | 1 | 100_files | 5 | 8.1545 | 0.4888 | 7.9694 | 9.1745 |
| main-dohq | copy_file | 1MB | 1 |  | 5 | 0.1616 | 0.0092 | 0.1472 | 0.168 |
| main-dohq | move_file | 1MB | 1 |  | 5 | 0.1657 | 0.0365 | 0.1619 | 0.2463 |
| main-dohq | remove_file | 1MB | 1 |  | 5 | 0.1304 | 0.006 | 0.1212 | 0.137 |
| main-dohq | put_archive | 1MB | 1 | zip | 5 | 0.4105 | 0.0424 | 0.3847 | 0.4858 |
| main-dohq | get_archive | 1MB | 1 | zip | 5 | 0.1148 | 0.1005 | 0.0978 | 0.3329 |
