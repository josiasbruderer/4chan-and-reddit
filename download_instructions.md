# Download Data

## Preparation

The toolbox will work without fully downloaded raw data (f.E. using a db dump). However, downloading all data will give full functionality.
Following these instructions will guide you through download process.

You will need to install following dependencies:

- `Bash` (on Linux/OSX you're probably all set, on Windows you could try: https://git-scm.com/download/win )
- `wget`
- `zstd`
- `pigz`

And you should have around 500GB free storage space (SSD highly preferred) for...

- ...temporary storage:
  - ~80GB for redarcs data
  - ~250GB for 4plebs data
  - ~90-160 GB for 4plebs thumbs
  - ~12GB for redarcs (archives)
  - ~70GB for 4plebs (archives)
- ...persistent storage:
  - ~25GB for database

## Test results

My test resulted in:

- Using one year of Data (analog to Hagen et al., selected subreddits comments, only /pol/):
  - Data: 145min; 23GB DB; ~49 Million Records
  - Images: 190min; 16GB DB; ~4 Million Records

## Download instructions

### Hagen et al. (Qanon specific data)

1. Download data

```bash
mkdir -p data/hagen-et-al/data_raw
wget -P data/hagen-et-al/data_raw https://zenodo.org/records/3758479/files/qanon_4chan.csv
wget -P data/hagen-et-al/data_raw https://zenodo.org/records/3758479/files/qanon_reddit.csv
```

2. Prepare testing data

```bash
mkdir -p data/hagen-et-al/data_test
head -n 1000 data/hagen-et-al/data_raw/qanon_4chan.csv > data/hagen-et-al/data_test/qanon_4chan.csv
tail -n 1000 data/hagen-et-al/data_raw/qanon_4chan.csv >> data/hagen-et-al/data_test/qanon_4chan.csv
head -n 1000 data/hagen-et-al/data_raw/qanon_reddit.csv > data/hagen-et-al/data_test/qanon_reddit.csv
tail -n 1000 data/hagen-et-al/data_raw/qanon_reddit.csv >> data/hagen-et-al/data_test/qanon_reddit.csv
gzip data/hagen-et-al/data_test/*
```

3. Compress raw data

```bash
#choose one of following:
for file in data/hagen-et-al/data_raw/*; do echo "$file"; pv "$file" | gzip > "${file}.gz" ; done  #for single core & slower disk
for file in data/hagen-et-al/data_raw/*; do echo "$file"; pv "$file" | pigz > "${file}.gz" ; done  #for multi core & faster disk
```


### Redarcs (Reddit)

1.  Download archives for required boards

```bash
mkdir -p data/redarcs/data_zipped
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/uspolitics_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/uspolitics_comments.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/worldpolitics_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/worldpolitics_comments.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/conspiracy_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/conspiracy_comments.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/Conservative_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/Conservative_comments.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/AskALiberal_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/AskALiberal_comments.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/anime_titties_submissions.zst
wget -P data/redarcs/data_zipped https://the-eye.eu/redarcs/files/anime_titties_comments.zst
```

2. Extract archives and clean up

```bash
zstd -d data/redarcs/data_zipped/*.zst
rm data/redarcs/data_zipped/*.zst
mv data/redarcs/data_zipped data/redarcs/data_raw
```

3. Prepare testing data

```bash
mkdir -p data/redarcs/data_test
redarcsBoards=("anime_titties" "AskALiberal" "Conservative" "conspiracy" "uspolitics" "worldpolitics")
for board in ${redarcsBoards[@]}; do
	for area in "comments" "submissions"; do
		echo "Processing: ${area} of ${board}"
		head -n 1000 data/redarcs/data_raw/${board}_${area} > data/redarcs/data_test/${board}_${area}
		tail -n 1000 data/redarcs/data_raw/${board}_${area} >> data/redarcs/data_test/${board}_${area}
	done
done
gzip data/redarcs/data_test/*
```

4. Compress raw data

```bash
#choose one of following:
for file in data/redarcs/data_raw/*; do echo "$file"; pv "$file" | gzip > "${file}.gz" ; done  #for single core & slower disk
for file in data/redarcs/data_raw/*; do echo "$file"; pv "$file" | pigz > "${file}.gz" ; done  #for multi core & faster disk
```


### 4plebs (4chan) data

1. Download data archives for required boards

```bash
mkdir -p data/4plebs/data_zipped
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/adv.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/f.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/hr.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/o.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/pol.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/s4s.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/sp.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/tg.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/trv.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/tv.csv.tar.gz
wget -P data/4plebs/data_zipped https://archive.org/download/4plebs-org-data-dump-2024-01/x.csv.tar.gz
```

2. Extract data archives and clean up

```bash
tar -xzf data/4plebs/data_zipped/*.tar.gz -C data/4plebs/data_zipped
rm data/4plebs/data_zipped/*.tar.gz
mv data/4plebs/data_zipped data/4plebs/data_raw2
```

3. Prepare testing data

```bash
mkdir -p data/4plebs/data_test
fourplebsBoards=("adv" "f" "hr" "o" "pol" "s4s" "sp" "tg" "trv" "tv" "x")
for board in ${fourplebsBoards[@]}; do
	echo "Processing: ${board}"
	head -n 1000 data/4plebs/data_raw/${board}.csv > data/4plebs/data_test/${board}.csv
	tail -n 1000 data/4plebs/data_raw/${board}.csv >> data/4plebs/data_test/${board}.csv
done
gzip data/4plebs/data_test/*.csv
```

4. Compress raw data

```bash
#split huge pol archive to 4 files: this will make processing much more memory efficient
board=pol
split -n 4 -d --filter='pigz > $FILE.csv.gz' ${board}.csv ${board}_  # TODO: check if command is valid! (just added .csv so that output path is pol_xx.csv.gz)

#choose one of following:
for file in data/4plebs/data_raw/*; do echo "$file"; pv "$file" | gzip > "${file}.gz" ; done  #for single core & slower disk
for file in data/4plebs/data_raw/*; do echo "$file"; pv "$file" | pigz > "${file}.gz" ; done  #for multi core & faster disk
```


### 4plebs (4chan) thumbs

1. Download thumbnail archives (tg and trv missing)
```bash
mkdir -p data/4plebs/thumbs_raw
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/adv_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/f_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/hr_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/o_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/pol_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/s4s_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/sp_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/tv_thumbs.tar.gz
wget -P data/4plebs/thumbs_zipped https://archive.org/download/4plebs-org-thumbnail-dump-2024-01/x_thumbs.tar.gz
```
