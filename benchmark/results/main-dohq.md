# Artifactory benchmark results: main-dohq

| label | operation | size | num_workers | extra | runs | median(s) | stdev(s) | min(s) | max(s) |
|---|---|---|---:|---|---:|---:|---:|---:|---:|
| main-dohq | put_file | 1KB | 1 |  | 20 | 0.2612 | 0.0342 | 0.2461 | 0.3688 |
| main-dohq | put_file | 1MB | 1 |  | 20 | 0.3061 | 0.0505 | 0.2901 | 0.5255 |
| main-dohq | put_file | 50MB | 1 |  | 20 | 1.1703 | 0.0694 | 1.0593 | 1.3138 |
| main-dohq | get_file | 1KB | 1 |  | 20 | 0.0762 | 0.0072 | 0.0749 | 0.1082 |
| main-dohq | get_file | 1KB | 6 |  | 20 | 0.0754 | 0.0014 | 0.0747 | 0.0793 |
| main-dohq | get_file | 1MB | 1 |  | 20 | 0.1288 | 0.0561 | 0.1214 | 0.3795 |
| main-dohq | get_file | 1MB | 6 |  | 20 | 0.1308 | 0.0047 | 0.1221 | 0.1387 |
| main-dohq | get_file | 50MB | 1 |  | 20 | 0.6323 | 0.0305 | 0.6287 | 0.7682 |
| main-dohq | get_file | 50MB | 6 |  | 20 | 0.6304 | 0.0052 | 0.6276 | 0.652 |
| main-dohq | exists | 1KB | 1 |  | 20 | 0.0381 | 0.004 | 0.0367 | 0.0554 |
| main-dohq | checksum | 1KB | 1 |  | 20 | 0.0389 | 0.0017 | 0.0372 | 0.0425 |
| main-dohq | date | 1KB | 1 |  | 20 | 0.0382 | 0.0022 | 0.0365 | 0.045 |
| main-dohq | owner | 1KB | 1 |  | 20 | 0.0386 | 0.0027 | 0.0363 | 0.0455 |
| main-dohq | ls | - | 1 | 10_files | 20 | 0.9218 | 0.2945 | 0.902 | 2.2278 |
| main-dohq | ls | - | 1 | 100_files | 20 | 8.172 | 0.2017 | 7.864 | 8.6953 |
| main-dohq | copy_file | 1MB | 1 |  | 20 | 0.1449 | 0.0029 | 0.1413 | 0.1529 |
| main-dohq | move_file | 1MB | 1 |  | 20 | 0.1577 | 0.0045 | 0.1521 | 0.1695 |
| main-dohq | remove_file | 1MB | 1 |  | 20 | 0.1186 | 0.0044 | 0.1144 | 0.1344 |
| main-dohq | put_archive | 1MB | 1 | zip | 20 | 0.3758 | 0.0426 | 0.3497 | 0.5106 |
| main-dohq | get_archive | 1MB | 1 | zip | 20 | 0.0944 | 0.0518 | 0.0882 | 0.326 |
