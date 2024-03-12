import os
import re
import argparse
from hashlib import md5

import requests as rq

ArgParser = argparse.ArgumentParser()
ArgParser.add_argument('--file-path', dest='fp', action='store', help='指定文件地址')


def get_file_name(url: str):
    m = md5()
    m.update(url.encode())
    return m.hexdigest()


def scan(fp: str, file_name: str, image_folder_path: str, download: bool = False):
    match_image = re.compile(r'(?P<front_part>.*)!\[(?P<reference_name>.*?)]\((?P<url>.+?)\)(?P<back_part>.*)')
    valid_http_url = re.compile(r'^https?://.+$')
    find_suffix = r'(?i)\.(jpg|png|jpeg)'
    has_download: set[str] = set()

    new_lines = []
    with open(fp, 'r', encoding='utf-8') as raw_file:
        for line in raw_file:
            match_result = match_image.match(line)

            # 不包含图片链接
            if match_result is None:
                if download:
                    new_lines.append(line)

            # 包含图片链接
            else:
                url = match_result.group('url')
                if valid_http_url.match(url) is None:
                    raise RuntimeError(f'不是一个合法的URL: {url}')
                suffix_result = re.findall(find_suffix, line)
                if len(suffix_result) == 0:
                    raise RuntimeError(f'查找不到图片后缀: {line}')
                suffix = suffix_result[0]

                # 如果启用下载
                if download is False:
                    continue
                hash_name = get_file_name(url)
                if hash_name in has_download:
                    continue

                # 下载和写入
                resp = rq.get(url, timeout=60, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
                })
                resp.raise_for_status()
                download_path = os.path.join(image_folder_path, f'{hash_name}.{suffix}')
                new_reference_path = f'{file_name}/{hash_name}.{suffix}'
                with open(download_path, 'wb') as image_file:
                    image_file.write(resp.content)
                has_download.add(hash_name)

                # 替换原文
                front_part = match_result.group('front_part')
                reference_name = match_result.group('reference_name')
                back_part = match_result.group('back_part')
                new_lines.append(
                    f'{front_part}![{reference_name}]({new_reference_path}){back_part}'.rstrip('\n') + '\n'
                )

    return new_lines


def main():
    cmd_args = ArgParser.parse_args()
    fp: str = cmd_args.fp
    if fp is None:
        raise RuntimeError('文件路径参数是必须的。')
    if os.path.exists(fp) is False or os.path.isfile(fp) is False:
        raise RuntimeError('文件路径不存在或者文件路径指向的不是一个文件。')
    fp = os.path.abspath(fp)
    file_name_suffix = os.path.splitext(fp)[1]
    file_name = os.path.split(fp)[1][: 0-len(file_name_suffix)]
    image_folder_path = fp[: 0-len(file_name_suffix)]

    os.makedirs(image_folder_path, exist_ok=True)

    scan(fp, file_name, image_folder_path)
    new_lines = scan(fp, file_name, image_folder_path, download=True)

    new_file_name = f'{file_name}_new.md'
    new_file_path = os.path.join(os.path.split(fp)[0], new_file_name)
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)


if __name__ == '__main__':
    main()
