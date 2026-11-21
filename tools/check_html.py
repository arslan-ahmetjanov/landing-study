#!/usr/bin/env python3
"""Проверки разметки лендинга без внешних зависимостей.

Запуск из корня репозитория: python tools/check_html.py [index.html]
Проверяет: уникальность id, существование целей у якорей, отсутствие
инлайновых обработчиков, alt у изображений, один h1, отсутствие пропусков
в иерархии заголовков, наличие main. Код возврата 1 при любой ошибке.
"""
import sys
from html.parser import HTMLParser

VOID = {'meta', 'link', 'br', 'hr', 'img', 'input', 'source', 'area',
        'base', 'col', 'embed', 'param', 'track', 'wbr'}


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.inline_handlers = []
        self.headings = []
        self.stack = []
        self.errors = []
        self.labels = []
        self.img_without_alt = 0
        self.has_main = False

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if 'id' in data:
            self.ids.append(data['id'])
        if data.get('href', '').startswith('#'):
            self.hrefs.append(data['href'])
        self.inline_handlers.extend((tag, name) for name in data if name.startswith('on'))
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.headings.append(int(tag[1]))
        if tag == 'main':
            self.has_main = True
        if tag == 'label' and 'for' in data:
            self.labels.append(data['for'])
        if tag == 'img' and 'alt' not in data:
            self.img_without_alt += 1
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append('лишний закрывающий тег ' + tag)
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append('несогласованные теги: открыт %s, закрыт %s' % (self.stack[-1], tag))
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass


def main(path):
    with open(path, encoding='utf-8') as f:
        html = f.read()

    parser = Checker()
    parser.feed(html)

    problems = []
    ids = parser.ids
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        problems.append('повторяющиеся id: ' + ', '.join(duplicates))

    id_set = set(ids)
    missing = sorted({h[1:] for h in parser.hrefs if h[1:] and h[1:] not in id_set})
    if missing:
        problems.append('якоря без цели: ' + ', '.join(missing))

    orphan_labels = sorted({f for f in parser.labels if f not in id_set})
    if orphan_labels:
        problems.append('label[for] без поля: ' + ', '.join(orphan_labels))

    if parser.inline_handlers:
        problems.append('инлайновые обработчики: ' +
                        ', '.join('%s@%s' % (t, a) for t, a in parser.inline_handlers))

    if parser.img_without_alt:
        problems.append('изображений без alt: %d' % parser.img_without_alt)

    if not parser.has_main:
        problems.append('нет элемента main')

    if parser.stack:
        problems.append('не закрыты теги: ' + ', '.join(parser.stack))

    problems.extend(parser.errors)

    if parser.headings.count(1) != 1:
        problems.append('ожидается ровно один h1, найдено %d' % parser.headings.count(1))

    skips = [(a, b) for a, b in zip(parser.headings, parser.headings[1:]) if b - a > 1]
    if skips:
        problems.append('пропуски в иерархии заголовков: ' +
                        ', '.join('h%d→h%d' % s for s in skips))

    if problems:
        for problem in problems:
            print('FAIL:', problem)
        return 1

    print('OK: %d id, %d якорей, %d заголовков' % (len(ids), len(parser.hrefs), len(parser.headings)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'index.html'))
