# use this script to import data to database
import os
from .processor import Processor
from packages import databaser
from packages import performancer


def start(config, action):
    if action == "import":
        proc = Processor(
            config.as_path(config.get_from_import_run_mode("db_name")),
            config.get("import", "chunk_size"),
            config.get("import", "num_workers"),
            config.get_from_import_run_mode("date_range"),
            config.get("general", "log_file"),
            None
        )

    if action == "images_import":
        proc = Processor(
            config.get('images_import', 'db_name'),
            config.get("images_import", "chunk_size"),
            config.get("images_import", "num_workers"),
            config.get("images_import", "date_range"),
            config.get("general", "log_file"),
            config.get('images_import', 'archive_org_dl_url')
        )

    if not proc:
        raise NotImplementedError("invalid action provided!")

    perf = performancer.Performancer(proc.debug)

    databaser.setup_database(
        proc.db_name,
        config.get(action, "init_script"),
        config.get(action, "drop_all_data")
    )

    if action == "import":
        file_exclusions = config.get_from_import_run_mode("file_exclusions")
        skip_import = config.get_from_import_run_mode("skip_import")

    if action == "images_import":
        file_exclusions = config.get("images_import", "file_exclusions")

    perf.start("global")

    current_file = 0

    if action == "import":
        # calculate total required files
        total_files = 2 if not skip_import or 'hagen' not in skip_import else 0
        total_files += sum([True if not file_exclusions or f not in file_exclusions else False for f in
                            os.listdir(config.get("import", "redarcs_data_dir"))]) if not skip_import or 'redarcs' not in skip_import else 0
        total_files += sum([True if not file_exclusions or f not in file_exclusions else False for f in
                            os.listdir(config.get("import", "fourplebs_data_dir"))]) if not skip_import or '4plebs' not in skip_import else 0

        if not skip_import or 'hagen' not in skip_import:
            data_dir = config.as_path(config.get("import", "hagen_data_dir"))

            perf.start("file")
            current_file += 1
            proc.start_import(os.path.join(data_dir, 'qanon_4chan.csv.gz'), 'q_4chan', total_files, current_file)
            perf.end("file", "Processing of file took")

            perf.start("file")
            current_file += 1
            proc.start_import(os.path.join(data_dir, 'qanon_reddit.csv.gz'), 'q_reddit', total_files, current_file)
            perf.end("file", "Processing of file took")

            perf.end("global", "Processing took", "so far")

        if not skip_import or 'redarcs' not in skip_import:
            data_dir = config.as_path(config.get("import", "redarcs_data_dir"))
            for file in sorted(os.listdir(data_dir)):
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path) and (not file_exclusions or file not in file_exclusions):
                    perf.start("file")
                    current_file += 1
                    mode = 'reddit_comments'
                    if str.endswith(file_path, "submissions.gz"):
                        mode = 'reddit_submissions'
                    proc.start_import(file_path, mode, total_files, current_file)
                    perf.end("file", "Processing of file took")

            perf.end("global", "Processing took", "so far")

        if not skip_import or '4plebs' not in skip_import:
            data_dir = config.get("import", "fourplebs_data_dir")
            for file in sorted(os.listdir(data_dir)):
                file_path = os.path.join(data_dir, file)
                if os.path.isfile(file_path) and (not file_exclusions or file not in file_exclusions):
                    perf.start("file")
                    current_file += 1
                    proc.start_import(file_path, '4chan', total_files, current_file)
                    perf.end("file", "Processing of file took")

            perf.end("global", "Processing took", "so far")

    if action == "images_import":
        # calculate total required files
        total_files = sum([True if not file_exclusions or f not in file_exclusions else False for f in
                           os.listdir(config.get("images_import", "fourplebs_images_meta_dir"))])
        total_files += sum([True if not file_exclusions or f not in file_exclusions else False for f in
                            os.listdir(config.get("images_import", "fourplebs_thumbs_dir"))])

        meta_data_dir = config.as_path(config.get("images_import", "fourplebs_images_meta_dir"))
        for file in sorted(os.listdir(meta_data_dir)):
            file_path = os.path.join(meta_data_dir, file)
            if os.path.isfile(file_path):
                current_file += 1
                if file_path.endswith('.xml'):
                    proc.start_import(file_path, '4chan_images', total_files, current_file)

        perf.end("global", "Processing took", "so far")

        data_dir = config.as_path(config.get("images_import", "fourplebs_thumbs_dir"))
        for file in sorted(os.listdir(data_dir)):
            file_path = os.path.join(data_dir, file)
            if os.path.isfile(file_path) and (not file_exclusions or file not in file_exclusions):
                current_file += 1
                perf.start("file")
                proc.debug(f'processing {file_path}')
                proc.start_import(file_path, '4chan_thumbs', total_files, current_file)
                perf.end("file", "Processing of file took")

    perf.end("global", "Processing took")
