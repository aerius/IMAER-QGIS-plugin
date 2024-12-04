import os
import argparse
import pathlib
import shutil

from build_config import build_config


def remove_country_code(fn, country_code):
    path = os.path.dirname(fn)
    basename = os.path.basename(fn)
    base, ext = os.path.splitext(basename)
    # print(path, basename, base, ext)

    if base.endswith(f'_{country_code}'):
        base = base[:-3]
    
    basename = f'{base}{ext}'
    return os.path.join(path, basename)

def clear_directory(dirname):
    ''' Makes sure an empty directory exist. '''
    if os.path.exists(dirname):
        for filename in os.listdir(dirname):
            file_path = os.path.join(dirname, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

def create_directory(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

if __name__ == '__main__':
    repository_path = os.path.dirname(__file__)
    print(repository_path)

    plugin_src_path = os.path.join(repository_path, 'ImaerPlugin')
    print(plugin_src_path)

    for country_code in ['nl', 'uk']:
        options = build_config['options'][country_code]
        plugin_dst_path = os.path.join(repository_path, 'output', options['plugin_dir_name'])
        print(plugin_dst_path)
        create_directory(plugin_dst_path)
        clear_directory(plugin_dst_path)

        files = build_config['files']['generic'] + build_config['files'][country_code]
        for file in files:
            src_fn = os.path.join(plugin_src_path, file)
            print(src_fn)
            dst_fn = os.path.join(plugin_dst_path, file)
            dst_fn = remove_country_code(dst_fn, country_code)
            print(dst_fn)
            create_directory(os.path.dirname(dst_fn))
            shutil.copyfile(src_fn, dst_fn)
            print()
