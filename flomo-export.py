"""
Author: bbruceyuan
Time: 2023/2/8

导出 flomo 的数据,
把从官网导出的 flomo 数据，导出成数据，共其他的 app 使用，比如 obsidian, typora, logseq,
"""
import argparse
import pathlib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

import bs4
from bs4 import BeautifulSoup


@dataclass
class Memo:
    """ memo 规则
    content: 正文内容
        - 普通的 p 标签
        - 加粗标签； 需要替换成 ****， 现在 parser 之前就 替换了；还有 B 标签
        - 有序列表
        - 无序列表；
        目前暂时不支持嵌套 （因为 flomo 不支持）
    """
    create_time: str
    content: str = ""
    file_list: Optional[List[str]] = None
    tag_list: Optional[List[str]] = None

    def __lt__(self, other):
        return self.create_time < other.create_time


def parse_file(file_path: pathlib.Path) -> List[Memo]:
    """
       html 格式：
        所有的日志放在 <div class="memos"></div> 中
        每一条日志是一个 <div class"memo"></div>

       example:
        <div class="memo">
            <div class="time">2021-03-29 18:07:06</div>
            <div class="content">
                <p>test</p><p></p><p>这东西还是挺有意思的</p>
            </div>
            <div class="files"></div>
        </div>

    """
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    # 提前替换<strong></strong> b 标签
    file_content = re.sub(r"<b>(.+?)</b>",
                          __bold_to_md_type, file_content, re.DOTALL)
    file_content = re.sub(r"<strong>(.+?)</strong>",
                          __bold_to_md_type, file_content, re.DOTALL)
    # todo: 除了 <p> 标签之外，还有 li/ui 标签需要考虑如何嵌套；这里也是建议 先用 markdown 语法替换；
    # 如果是导入到 标准的 markdown 中，比如 obsidian, 还可以把 li 之类的东西加上。

    tree = BeautifulSoup(file_content, 'html.parser')

    one_file_memos = []
    for item in tree.find_all("div", class_="memo"):
        # 把文件中的 所有 memo 都 parse 了；
        one_memo = _parse_one_memo(item)
        one_file_memos.append(one_memo)

    return one_file_memos


def __bold_to_md_type(match_obj):
    return "**{}**".format(match_obj.group(1))


def _parse_one_memo(item) -> Memo:
    ret = {}
    time_item = item.find("div", class_="time")
    # 所有的 content 都在这一步
    content_parent = item.find("div", class_="content")

    raw_contents: List[bs4.element.NavigableString] = content_parent.contents
    # 得到 content 和 tag_list
    clearn_markdown_content, tag_list = _memo_content_clean(raw_contents)
    ret.update({
        "content": clearn_markdown_content,
        "tag_list": tag_list
    })

    # todo: 这里仅仅是找到 image list, 可能有人需要支持语音，因为我没有图片，所以我实际上也没有导出图片
    file_items = item.find_all("img")
    if len(file_items) != 0:
        image_srcs_list = [
            file_item["src"] for file_item in file_items
        ]
        ret.update({
            "file_list": image_srcs_list
        })

    ret.update({
        "create_time": time_item.getText()
    })
    memo = Memo(**ret)
    return memo


def _memo_content_clean(content_elements: List[bs4.element.NavigableString]) -> Tuple[str, List[str]]:
    """
        如果是无序列表，那么等就是把  ol 换成 ul
        <ol>
            <li>
                <p>数据增强的方式，同义词替换。同标签词替换？需要考虑</p>
            </li>
            <li>
                <p>context representation 的表示。</p>
            </li>
        </ol>

    """
    tag_list = []
    markdown_ret = []
    for item in content_elements:
        tag_list_tmp, markdown_without_tag = _extract_tag_from_content(item)
        tag_list.extend(tag_list_tmp)
        if markdown_without_tag:
            markdown_ret.append(markdown_without_tag)

    return "\n\n".join(markdown_ret), tag_list


def _extract_tag_from_content(content_: Any) -> Tuple[List[str], str]:
    def _extract_tag_from_str(content: str) -> Tuple[List[str], str]:
        # TAG 在 logseq 和 obsidian 是不一样的。
        if not content:
            return [], content
        else:
            tag_list = re.findall(r'(#.+?\s+?)', content, re.DOTALL)
            tag_list = list(map(lambda x: x.strip(), tag_list))

            content = re.sub(r'(#.+?\s+?)', "", content, re.DOTALL).strip()

            # 特殊的 TAG, 假设这一行只有 TAG, 那么上面的规则不可靠
            match_obj = re.match(r"^(#.+?)$", content.strip())
            if match_obj and not re.search(r"\s", content):
                tag_list.append(match_obj.group(1))
                content = re.sub(r"^(#.+?)$", "", content, re.DOTALL).strip()

            return list(set(tag_list)), content
        # _extract_tag_from_str()  function end

    ret_tag_list = []
    ret_content = []
    for one_item_element in content_.stripped_strings:
        ret_tag_list_tmp, ret_tmp = _extract_tag_from_str(one_item_element)
        ret_tag_list.extend(ret_tag_list_tmp)
        ret_content.append(ret_tmp)
    return list(set(ret_tag_list)), "\n".join(ret_content)


def write_memo_as_md(memos: List[Memo], file_path: Optional[pathlib.Path] = None) -> None:
    def _memo_to_md(one_memo: Memo) -> str:
        ret = "- {}".format(one_memo.create_time)
        if one_memo.tag_list:
            ret += "  ,  {}".format(" ".join(one_memo.tag_list))
        ret += "\n\n"
        contents = one_memo.content.split("\n")
        for one_line in contents:
            if one_line:
                ret += "\t" + one_line + '\n\n'
                
        if one_memo.file_list:
            print(one_memo.file_list)
            for file in one_memo.file_list:
                ret += "\n\n"
                ret += f"![{file}]({file})"

        # 如果是导入到 logseq 中，使用下面的三行
        # ret += "\t- " + one_memo.content
        ret += "\n\n"
        return ret

    memos = sorted(memos)
    with file_path.open('w', encoding='utf-8') as f:
        for memo in memos:
            tmp = _memo_to_md(memo)
            f.write(tmp)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="flomo_export.md",
                        help="输出路径")
    parser.add_argument("--input", default=".",
                        help="输入的文件位置，默认是当前路径")
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    cur_path = pathlib.Path(args.input)
    html_files = cur_path.glob("**/*.html")
    memos = []
    for file in html_files:
        memos.extend(parse_file(file))
    write_memo_as_md(memos, pathlib.Path(args.out))


if __name__ == '__main__':
    main()
