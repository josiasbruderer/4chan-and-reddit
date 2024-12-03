import csv
import json
import os
import shutil
import time

from packages import logger
from packages import performancer
from packages import databaser
from .query import querymanager
from pandas_ods_reader import read_ods


def start(config, ACTION, reliability_test = False):
    log = logger.setup(__name__, config.get("general", "log_file"), logger.DEBUG)
    perf = performancer.Performancer(log.debug)
    results_dir = config.as_path(config.get('analysis', 'results_dir'))
    results_dir = os.path.join(results_dir, time.strftime("%Y-%m-%d_%H-%M-%S"))
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    result_df_path_csv = os.path.join(results_dir, "analysis.csv")
    result_df_path_json = os.path.join(results_dir, "analysis.json")
    result_meta_json = os.path.join(results_dir, "meta.json")
    result_diggdeep_dir = os.path.join(results_dir, 'comments')
    if not os.path.exists(result_diggdeep_dir):
        os.makedirs(result_diggdeep_dir)
    sample_path = {
        '4chan': os.path.join(results_dir, "sample_4chan.json"),
        'reddit': os.path.join(results_dir, "sample_reddit.json"),
        '4chan_full': os.path.join(results_dir, "sample_4chan_full"),
        'reddit_full': os.path.join(results_dir, "sample_reddit_full")
    }
    sample_ratio = config.get('analysis', 'sample_ratio')
    sample_size = {
        '4chan': 0,
        'reddit': 0
    }
    try:
        shutil.copyfile(config.get("analysis", "html_template"), os.path.join(results_dir, 'index.html'))
    except Exception as e:
        log.warning('index.html was not copied')
    try:
        shutil.copyfile(config.get("analysis", "favicon"), os.path.join(results_dir, 'favicon.ico'))
    except Exception as e:
        log.warning('favicon.ico was not copied')

    qm = querymanager()

    conn = databaser.connect_database_ro(config.as_path(config.get_from_import_run_mode("db_name")))

    if ACTION == "analyse":
        markers_ods_path = config.as_path(config.get('analysis', 'markers_ods'))
        markers_df = read_ods(markers_ods_path, "full")
        analyse_df = markers_df[markers_df["to_analyse"] == 1]
        analyse_df = analyse_df[60:63]  # limit df to 3 rows for testing :)
        analyse_df = analyse_df.reset_index()

        # create sample
        sample = {}
        sample_mode = config.get('analysis', 'sample_mode')
        for platform in ['4chan', 'reddit']:
            if sample_mode == 'hagen':
                log.info("creating sample for " + platform + " using same amount of posts as Hagen et al. (2020)")
                sample[platform] = qm.query_sample(conn, "create_sample", {'platform': platform})
            elif sample_mode == 'ratio':
                log.info(f'creating sample for {platform} using {sample_ratio[platform]}% of all data')
                sample[platform] = qm.query_sample(conn, "create_sample_bypercent", {'platform': platform, 'sample_ratio': sample_ratio[platform]})
            elif sample_mode == 'weighted':
                log.info(f'creating sample for {platform} using weights and total of {config.get('analysis', 'total_sample_size')} posts of all data')
                sample[platform] = qm.query_sample(conn, "create_sample_weighted", {'platform': platform, 'total_sample_size': config.get('analysis', 'total_sample_size')})
            else:
                log.info("creating sample for " + platform + " using 1% of all data")
                sample[platform] = qm.query_sample(conn, "create_sample_bypercent", {'platform': platform, 'sample_ratio': 100})
            sample_dump = qm.query_sample(conn, "dump_sample", sample_name=sample[platform])
            sample_dump = [s[0] for s in sample_dump[1]]
            sample_size[platform] = len(sample_dump)
            if not config.get('analysis', 'dryrun'):
                with open(sample_path[platform], 'w', encoding="utf-8") as file:
                    json.dump(sample_dump, file)
                sample_dump2 = qm.query_sample(conn, "dump_sample2", sample_name=sample[platform])
                with open(sample_path[platform + "_full"] + ".json", 'w', encoding="utf-8") as file:
                    json.dump(sample_dump2, file)
                with open(sample_path[platform + "_full"] + ".csv", 'w', encoding="utf-8", newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(sample_dump2[0])
                    for row in sample_dump2[1]:
                        writer.writerow(row)
        log.info(f'Sample sizes using {sample_mode} mode: {sample_size}')

        # describe data
        log.info("analyzing descriptive")
        meta_data = {
            'counts_per_board': qm.query(conn, "counts_per_board"),
            'counts_per_platform': qm.query(conn, "counts_per_platform"),
            'sample_size': sample_size,
            'distribution_per_date': qm.query_sample(conn, "meta_posts_per_day", sample_name=[sample['4chan'], sample['reddit']])
        }
        if not config.get('analysis', 'dryrun'):
            with open(result_meta_json, 'w', encoding="utf-8") as file:
                json.dump(meta_data, file)

        # run all queries
        keeper = {
            'count': {
                'all': [],  # this stores counts of all data
                'qanon': [],  # this stores counts of hagen et al. dataset
                'sample': []  # this stores counts of sample
            },
            'count_rel': {
                'all': [],  # this stores counts of all data
                'qanon': [],  # this stores counts of hagen et al. dataset
                'sample': []  # this stores counts of sample
            },
            'match': {
                'all': [],  # this stores counts of all data
                'qanon': [],  # this stores counts of hagen et al. dataset
                'sample': []  # this stores counts of sample
            },
            'match_ratio': {
                'all': [],  # this stores counts of all data
                'qanon': [],  # this stores counts of hagen et al. dataset
                'sample': []  # this stores counts of sample
            },
            'digg': {
                'all': [],  # this stores counts of all data
                'qanon': [],  # this stores counts of hagen et al. dataset
                'sample': []  # this stores counts of sample
            }
        }

        for idx, row in analyse_df.iterrows():
            try:
                digg_data = []   # this stores all found data rows
                log.info("Processing " + str(idx + 1) + " of " + str(len(analyse_df)) + ": " + row["fts_query"] + " for " + row["platform"]+ ", q_" + row["platform"] + " and " + sample[row["platform"]])
                count, digg = qm.query(conn, 'fts_body_count_by_platform', {'keyword': row["fts_query"], 'platform': row["platform"]}, format="single", deepdigg=True)
                count_q, digg_q = qm.query(conn, 'fts_body_count_by_platform', {'keyword': row["fts_query"], 'platform': "q_" + row["platform"]}, format="single", deepdigg=True)
                count_s, digg_s = qm.query_sample(conn, "fts_body_count_in_sample", {'keyword': row["fts_query"]}, sample[row["platform"]], format="single", deepdigg=True)

                if type(count) is int:
                    keeper['count']['all'].append(count)
                    try:
                        keeper['count_rel']['all'].append('{0:.10f}'.format(count / next(value for key, value in meta_data["counts_per_platform"][1] if key == row["platform"])))
                    except Exception as e:
                        keeper['count_rel']['all'].append(-1)
                        log.warning("calculating count_rel failed. ")
                    keeper['match']['all'].append(sum([str.count(d[14], '<span class="fts_match">') for d in digg]))
                    try:
                        keeper['match_ratio']['all'].append(1 / count * sum([str.count(d[14], '<span class="fts_match">') for d in digg]))
                    except Exception as e:
                        keeper['match_ratio']['all'].append(-1)
                        log.warning("calculating match_ratio failed. ")
                    keeper['digg']['all'].append([d[0] for d in digg])
                    digg_data += digg
                else:
                    log.warning("invalid result. probably some error? --> " + str(digg))
                    keeper['count']['all'].append(-1)
                    keeper['count_rel']['all'].append(-1)
                    keeper['match']['all'].append(-1)
                    keeper['match_ratio']['all'].append(-1)
                    keeper['digg']['all'].append([])

                if type(count_q) is int:
                    keeper['count']['qanon'].append(count_q)
                    try:
                        keeper['count_rel']['qanon'].append('{0:.10f}'.format(count_q / next(value for key, value in meta_data["counts_per_platform"][1] if key == 'q_' + row["platform"])))
                    except Exception as e:
                        keeper['count_rel']['qanon'].append(-1)
                    keeper['match']['qanon'].append(sum([str.count(d[14], '<span class="fts_match">') for d in digg_q]))
                    try:
                        keeper['match_ratio']['qanon'].append(1 / count_q * sum([str.count(d[14], '<span class="fts_match">') for d in digg_q]))
                    except Exception as e:
                        keeper['match_ratio']['qanon'].append(-1)
                        log.warning("calculating match_ratio failed. ")
                    keeper['digg']['qanon'].append([d[0] for d in digg_q])
                    digg_data += digg_q  # we need to store digg_q since they have differing uids!
                else:
                    log.warning("invalid result. probably some error? --> " + str(digg_q))
                    keeper['count']['qanon'].append(-1)
                    keeper['count_rel']['qanon'].append(-1)
                    keeper['match']['qanon'].append(-1)
                    keeper['match_ratio']['qanon'].append(-1)
                    keeper['digg']['qanon'].append([])

                if type(count_s) is int:
                    keeper['count']['sample'].append(count_s)
                    try:
                        keeper['count_rel']['sample'].append('{0:.10f}'.format(count_s / meta_data["sample_size"][row["platform"]]))
                    except Exception as e:
                        keeper['count_rel']['sample'].append(-1)
                    keeper['match']['sample'].append(sum([str.count(d[14], '<span class="fts_match">') for d in digg_s]))
                    try:
                        keeper['match_ratio']['sample'].append(1 / count_s * sum([str.count(d[14], '<span class="fts_match">') for d in digg_s]))
                    except Exception as e:
                        keeper['match_ratio']['sample'].append(-1)
                        log.warning("calculating match_ratio failed. ")
                    keeper['digg']['sample'].append([d[0] for d in digg_s])
                    # digg_data += digg_s  # we do not need to store digg_s since it is already included in digg
                else:
                    log.warning("invalid result. probably some error? --> " + str(digg_s))
                    keeper['count']['sample'].append(-1)
                    keeper['count_rel']['sample'].append(-1)
                    keeper['match']['sample'].append(-1)
                    keeper['match_ratio']['sample'].append(-1)
                    keeper['digg']['sample'].append([])
                if not config.get('analysis', 'dryrun'):
                    with open(os.path.join(result_diggdeep_dir, row["index"] + ".json"), 'w', encoding="utf-8") as file:
                        json.dump(list(set(digg_data)), file)
            except Exception as e:
                log.warning("something failed... we will skip this and continue with next one. error was: " + str(e))

        analyse_df['count_all'] = keeper['count']['all']
        analyse_df['count_all_rel'] = keeper['count_rel']['all']
        analyse_df['count_qanon'] = keeper['count']['qanon']
        analyse_df['count_qanon_rel'] = keeper['count_rel']['qanon']
        analyse_df['count_sample'] = keeper['count']['sample']
        analyse_df['count_sample_rel'] = keeper['count_rel']['sample']

        analyse_df['match_all'] = keeper['match']['all']
        analyse_df['match_all_ratio'] = keeper['match_ratio']['all']
        analyse_df['match_qanon'] = keeper['match']['qanon']
        analyse_df['match_qanon_ratio'] = keeper['match_ratio']['qanon']
        analyse_df['match_sample'] = keeper['match']['sample']
        analyse_df['match_sample_ratio'] = keeper['match_ratio']['sample']

        log.info("saving results to csv")
        if not config.get('analysis', 'dryrun'):
            analyse_df.to_csv(result_df_path_csv, sep=',', encoding='utf-8', index=False)

        analyse_df['digg_all'] = keeper['digg']['all']
        analyse_df['digg_qanon'] = keeper['digg']['qanon']
        analyse_df['digg_sample'] = keeper['digg']['sample']

        log.info("saving results to json")
        if not config.get('analysis', 'dryrun'):
            analyse_df.to_json(result_df_path_json, orient='records')

        for platform in ['4chan', 'reddit']:
            qm.query_sample(conn, "delete_sample", sample_name=sample[platform])

        log.info("analysis done!")
