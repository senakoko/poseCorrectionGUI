import re
import glob
import skimage.io as sk
import argparse
from pathlib import Path
import shutil
import yaml


def modify_config_2add_labeled_data(config_path: str = None,
                                    labeled_data_path: str = None,
                                    ) -> None:
    if config_path is None:
        print('Provide the path to the config.yaml file')
        return
    if labeled_data_path is None:
        print('Provide the path to the labeled data')
        return

    files = sorted(glob.glob(f'{labeled_data_path}/*', recursive=True))

    files_new = []
    for file in files:
        if re.search('_labeled', file) or re.search('_cropped', file):
            continue
        files_new.append(file)

    labeled_data = {}
    for file in files_new:
        file_p = Path(file)
        image_files = glob.glob(f"{file}/*.png")
        img_file_path = image_files[0]
        img = sk.imread(img_file_path)
        shape = img.shape
        dlc_format = f'0, {shape[1]}, 0, {shape[0]}'
        text = str(file_p.parent) + '/' + file_p.stem + '.mp4'
        crops = {'crop': dlc_format}
        labeled_data[text] = crops
        # print(crops)

    old_config_path = Path(config_path)
    old_config_path = str(old_config_path.parent) + '/' + old_config_path.stem + '_orig.yaml'
    shutil.copy(config_path, old_config_path)
    # print(labeled_data)

    comment_list = {'Task': '    # Project definitions (do not edit)\n',
                    'project_path': '    # Project path (change when moving around)\n',
                    'video_sets': '   # Annotation data set configuration (and individual video cropping parameters)\n',
                    'start': '    # Fraction of video to start/stop when extracting frames for labeling/refinement\n',
                    'skeleton': '    # Plotting configuration\n',
                    'TrainingFraction': '    # Training,Evaluation and Analysis configuration\n',
                    'cropping': '    # Cropping Parameters (for analysis and outlier frame detection)\n',
                    'x1': '    #if cropping is true for analysis, then set the values here:\n',
                    'corner2move2': '    # Refinement configuration (parameters from annotation dataset configuration '
                                    'also relevant in this stage)\n '
                    }

    with open(config_path, 'r') as fr:
        config = yaml.load(fr, yaml.FullLoader)
        config['video_sets'] = labeled_data

    with open(config_path, 'w') as fw:
        for key in config.keys():
            new_dict = {key: config[key]}
            if key in comment_list.keys():
                fw.write(comment_list[key])
            yaml.dump(new_dict, fw, default_flow_style=False, sort_keys=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='modify_config_2add_labeled_data',
                                     description='Modify the config.yaml file to include information '
                                                 'about the labeled data',
                                     epilog='Modifying config.yaml')
    parser.add_argument('-cp', '--config_path', action='store',
                        type=str, help='Provide the path of the config file', required=True)
    parser.add_argument('-l', '--labeled_data_path', action='store',
                        type=str, help='Provide the parent path to the video', required=True)
    args, _ = parser.parse_known_args()
    modify_config_2add_labeled_data(config_path=args.config_path,
                                    labeled_data_path=args.labeled_data_path)
