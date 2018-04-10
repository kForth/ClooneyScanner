import json
import sqlite3

import xlsxwriter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from tba_py import TBA


class SpreadsheetGenerator:
    def __init__(self, db_path, tba):
        self.db_path = db_path
        self.tba = tba

        self.workbook = None
        self.formats = None
        self.headers = None
        self.event = None
        self.raw_entries = None
        self.teams = None
        self.matches = None

        self.page_names = {
            'raw':                  'raw_data',
            'raw_calculated':       'raw_calculated',
            'raw_analysis':         'raw_analysis',
            'raw_team_list':        'raw_team_list',
            'raw_matches':          'raw_matches',
            'raw_team_schedule':    'raw_team_schedule',
            'pretty_raw':           'Raw Data',
            'pretty_team_list':     'Team List',
            'pretty_analysis':      'Analysis',
            'pretty_matches':       'Schedule',
            'pretty_team_schedule': 'Team Schedule',
            'team_stats':           'Team Stats',
            'match_rundown':        'Match Rundown'
        }

        self.raw_formats = json.load(open('formats.json'))

        self.range_formats = {
            'max_green': {
                'type':      '2_color_scale',
                'min_color': "#FFFFFF",
                'max_color': "#66BB6A"
            },
            'max_red':   {
                'type':      '2_color_scale',
                'min_color': "#FFFFFF",
                'max_color': "#EF5350"
            }
        }

    def create_spreadsheet_for_event(self, event_id, filename='Clooney.xlsx'):
        self.workbook = xlsxwriter.Workbook(filename)
        self.formats = dict([(k, self.workbook.add_format(v)) for k, v in self.raw_formats.items()])

        db = sqlite3.connect(self.db_path)
        self.headers = json.load(open('headers.json'))
        self.event = db.execute('SELECT * FROM events WHERE id = "{}"'.format(event_id)).fetchone()
        self.raw_entries = [json.loads(e[-2]) for e in
                            db.execute('SELECT * FROM scouting_entries WHERE event = "{}"'.format(event_id)).fetchall()]
        self.teams = sorted(json.loads(self.event[2]), key=lambda x: int(x['team_number']))
        self.matches = sorted([e for e in self.tba.get_event_matches(event_id) if e['comp_level'] == 'qm'],
                              key=lambda x: x['match_number'])
        for match in self.matches:
            for alli in ['red', 'blue']:
                for i in range(3):
                    match[alli + '_' + str(i + 1)] = int(match['alliances'][alli]['team_keys'][i][3:])

        self.draw_pretty_analysis()
        self.draw_pretty_match_rundown()
        self.draw_pretty_team_stats()
        self.draw_pretty_team_schedule()
        self.draw_pretty_schedule()
        self.draw_pretty_team_list()
        self.draw_pretty_raw_data()

        self.draw_raw_data()
        self.draw_raw_calculated()
        self.draw_raw_analysis()
        self.draw_raw_team_list()
        self.draw_raw_schedule()
        self.draw_raw_team_matches()

        self.workbook.close()
        self.workbook = None

    @staticmethod
    def next_col(col, i=1):
        col = list(col)
        while i > 0:
            if col[-1] == 'Z':
                col[-1] = 'A'
                col.append('A')
            else:
                col[-1] = chr(ord(col[-1]) + 1)
            i -= 1
        return "".join(col)

    def name_col(self, name, page, col, num_rows=999, start_row=1):
        self.workbook.define_name(name, "='{0}'!{1}{3}:{1}{2}".format(page, col, num_rows + start_row, start_row))

    def name_range(self, name, page, start_row=None, start_col='A', end_col='Z', end_row=None):
        range_str = "='{0}'!{1}{3}:{2}{4}".format(page, start_col, end_col,
                                                  start_row if start_row is not None else "",
                                                  (end_row if end_row is not None else start_row)
                                                  if start_row is not None else "")
        self.workbook.define_name(name, range_str)

    def draw_raw_data(self):
        page_name = self.page_names['raw']
        headers = self.headers['raw']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        col = 'A'
        row = 1
        header_cols = {}
        data_len = len(self.raw_entries)
        for header in headers:
            sheet.write(self.get_cell(col, row), header['title'])
            self.name_col('raw_{}'.format(header['key']), page_name, col, data_len + 1)
            header_cols[header['key']] = col
            col = self.next_col(col)

        for i in range(data_len):
            for header in headers:
                col = header_cols[header['key']]
                val = self.raw_entries[i][header['key']]
                sheet.write(self.get_cell(col, i + 2), val, self.formats['raw_data_cell'])

    def draw_raw_calculated(self):
        page_name = self.page_names['raw_calculated']
        headers = self.headers['raw_calculated']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        data_len = len(self.raw_entries)
        col = 'A'
        for header in headers:
            sheet.write(self.get_cell(col, 1), header['title'])
            self.name_col('raw_calculated_{}'.format(header['key']), page_name, col, data_len + 1)
            for i in range(data_len):
                sheet.write(self.get_cell(col, i + 2), header['value'], self.formats['raw_data_cell'])
            col = self.next_col(col)

    def draw_raw_analysis(self):
        page_name = self.page_names['raw_analysis']
        headers = self.headers['analysis']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        num_teams = len(self.teams)

        functions = {
            'avg': '=IF(ISBLANK(analysis_team_number), "", SUMIF(raw_team_number, "="&analysis_team_number, {}) / analysis_match)',
            'sum': '=IF(ISBLANK(analysis_team_number), "", SUMIF(raw_team_number, "="&analysis_team_number, {}))'
        }

        col = 'A'
        for header in headers:
            sheet.write(self.get_cell(col, 1), header['title'])
            self.name_col('analysis_{}'.format(header['key']), page_name, col, num_teams + 1)
            for i in range(num_teams):
                if header['key'] == 'team_number':
                    sheet.write(self.get_cell(col, i + 2), self.teams[i]['team_number'], self.formats['raw_data_cell'])
                elif 'func' in header.keys():
                    value = functions[header['func']].format('raw_{}'.format(header['key']))
                    sheet.write(self.get_cell(col, i + 2), value, self.formats['raw_data_cell'])
                else:
                    sheet.write(self.get_cell(col, i + 2), header['value'], self.formats['raw_data_cell'])
            col = self.next_col(col)

    def draw_raw_team_list(self):
        page_name = self.page_names['raw_team_list']
        headers = self.headers['team_list']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        data_len = len(self.teams)
        col = 'A'
        for header in headers:
            sheet.write(self.get_cell(col, 1), header['title'])
            self.name_col('team_list_{}'.format(header['key']), page_name, col, data_len + 1)
            if header['key'] == 'team_number':
                self.name_col('team_number_list', page_name, col, data_len, 2)
            for i in range(data_len):
                sheet.write(self.get_cell(col, i + 2), self.teams[i][header['key']], self.formats['raw_data_cell'])
            col = self.next_col(col)

    def draw_raw_team_matches(self):
        page_name = self.page_names['raw_team_schedule']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        data_len = len(self.teams)
        col = 'A'
        sheet.write(self.get_cell(col, 1), 'Team Number')
        self.name_col('team_schedule_team_number', page_name, col)
        for i in range(data_len):
            sheet.write(self.get_cell(col, i + 2), self.teams[i]['team_number'], self.formats['raw_data_cell'])
        col = self.next_col(col)

        sheet.write(self.get_cell(col, 1), 'Matches')
        self.name_range('team_schedule_matches', page_name,
                        start_col=col, end_col=self.next_col(col, 20))
        for i in range(data_len):
            for j in range(20):
                sheet.write_array_formula(
                        "{0}:{0}".format(self.get_cell(self.next_col(col, j), i + 2)),
                        "=ArrayFormula(IFERROR(SMALL(IF(schedule_match_teams=$A{0},ROW(schedule_red_1)-1), ROW({1}:{1}))))".format(
                                i + 2, j + 1),
                        self.formats['raw_data_cell']
                )

    def draw_raw_schedule(self):
        page_name = self.page_names['raw_matches']
        headers = self.headers['matches']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('red')
        sheet.hide()
        data_len = len(self.matches)
        col = 'A'
        red_1_col = col
        blue_3_col = col
        for header in headers:
            sheet.write(self.get_cell(col, 1), header['title'])
            self.name_col('schedule_{}'.format(header['key']), page_name, col, data_len + 1)
            if header['key'] == 'red_1':
                red_1_col = col
            elif header['key'] == 'blue_3':
                blue_3_col = col
            for i in range(data_len):
                sheet.write(self.get_cell(col, i + 2), self._get_data(self.matches[i], header['key']),
                            self.formats['raw_data_cell'])
            col = self.next_col(col)
        self.workbook.define_name(
                'schedule_match_teams',
                "='{0}'!{1}:{2}".format(page_name, red_1_col, blue_3_col)
        )

    def draw_pretty_raw_data(self):
        page_name = self.page_names['pretty_raw']
        raw_headers = self.headers['raw']
        calc_headers = self.headers['raw_calculated']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('blue')
        col = 'A'
        row = 1
        data_len = len(self.raw_entries)
        for header in raw_headers:
            sheet.write(
                    self.get_cell(col, row),
                    header['title'],
                    self.formats[header['header_format'] if 'header_format' in header.keys() else 'pretty_header']
            )
            for i in range(data_len):
                val = '=raw_{}'.format(header['key'])
                sheet.write(self.get_cell(col, i + 2), val, self.formats[header['format'] if 'format' in header.keys() else 'pretty_data_cell'])
            col = self.next_col(col)

        for header in calc_headers[3:]:
            sheet.write(
                    self.get_cell(col, row),
                    header['title'],
                    self.formats[header['header_format'] if 'header_format' in header.keys() else 'pretty_header']
            )
            for i in range(data_len):
                val = '=raw_calculated_{}'.format(header['key'])
                sheet.write(self.get_cell(col, i + 2), val, self.formats[header['format'] if 'format' in header.keys() else 'pretty_data_cell'])
            col = self.next_col(col)

    def draw_pretty_team_list(self):
        page_name = self.page_names['pretty_team_list']
        headers = self.headers['team_list']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('blue')
        sheet.set_default_row(16, True)
        sheet.set_row(0, 35)
        data_len = len(self.teams)
        col = 'A'
        for header in headers:
            sheet.write(
                    self.get_cell(col, 1),
                    header['title'],
                    self.formats[header['header_format']] if 'format' in header.keys()
                    else self.formats['pretty_header']
            )
            options = {}
            if "hidden" in header.keys():
                options['hidden'] = header['hidden']
            sheet.set_column(self.get_col_range(col),
                             width=header['width'] if "width" in header.keys() else 8,
                             options=options)
            for i in range(data_len):
                sheet.write(
                        self.get_cell(col, i + 2),
                        self.teams[i][header['key']],
                        self.formats[header['format']] if 'format' in header.keys()
                        else self.formats['pretty_data_cell']
                )
            col = self.next_col(col)

    def draw_pretty_schedule(self):
        page_name = self.page_names['pretty_matches']
        headers = self.headers['matches']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('blue')
        sheet.set_default_row(16, True)
        sheet.set_row(0, 35)
        data_len = len(self.matches)
        col = 'A'
        for header in headers:
            sheet.write(
                    self.get_cell(col, 1),
                    header['title'],
                    self.formats[header['header_format']] if 'format' in header.keys() else self.formats[
                        'pretty_header']
            )
            options = {}
            if "hidden" in header.keys():
                options['hidden'] = header['hidden']
            for i in range(data_len):
                sheet.write(
                        self.get_cell(col, i + 2),
                        self._get_data(self.matches[i], header['key']),
                        self.formats[header['format']] if 'format' in header.keys() else self.formats[
                            'pretty_data_cell']
                )
            sheet.set_column(self.get_col_range(col),
                             width=header['width'] if "width" in header.keys() else 8,
                             options=options)
            # if header['title'] == 'Red Score':
            #     sheet.conditional_format(self.get_col_range(col, 2, data_len), {
            #         'type':               'formula',
            #         'criteria':           '{0}2>{1}2'.format(col, self.next_col(col)),
            #         'format': self.formats['bold']
            #     })
            #     sheet.conditional_format(self.get_col_range(self.next_col(col), 2, data_len), {
            #         'type':               'formula',
            #         'criteria':           '{0}2>{1}2'.format(self.next_col(col), col),
            #         'format': self.formats['bold']
            #     })
            col = self.next_col(col)

    def draw_pretty_analysis(self):
        page_name = self.page_names['pretty_analysis']
        headers = self.headers['analysis']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('green')
        sheet.set_default_row(16, True)
        sheet.set_row(0, 70)
        data_len = len(self.teams)
        col = 'A'
        team_num_col = col
        for header in headers:
            sheet.write(
                    self.get_cell(col, 1),
                    header['title'],
                    self.formats[header['header_format']] if 'header_format' in header.keys()
                    else self.formats['pretty_header']
            )
            options = {}
            if "hidden" in header.keys():
                options['hidden'] = header['hidden']
            sheet.set_column(self.get_col_range(col), header['width'] if "width" in header.keys() else 8,
                             options=options)
            if header['key'] != 'team_number':
                if "scale" in header.keys():
                    sheet.conditional_format(self.get_col_range(col, 2, data_len), {
                        'type':     'cell',
                        'criteria': '=',
                        'value':    0,
                        'format':   self.formats[header['format']] if 'format' in header.keys()
                                    else self.formats['pretty_data_cell']
                    })
                    sheet.conditional_format(self.get_col_range(col, 2, data_len), self.range_formats[header['scale']])
            for i in range(data_len):
                if header['key'] == 'team_number':
                    sheet.write(
                            self.get_cell(col, i + 2),
                            self.teams[i]['team_number'],
                            self.formats[header['format']] if 'format' in header.keys()
                            else self.formats['pretty_data_cell']
                    )
                    team_num_col = col
                else:
                    formula = '=LOOKUP({0}, analysis_team_number, {1})'.format(
                            self.get_col_range(team_num_col),
                            'analysis_' + header['key']
                    )
                    sheet.write(
                            self.get_cell(col, i + 2),
                            formula,
                            self.formats[header['format']] if 'format' in header.keys()
                            else self.formats['pretty_data_cell']
                    )
            col = self.next_col(col)

    def draw_pretty_team_schedule(self):
        page_name = self.page_names['pretty_team_schedule']
        headers = self.headers['matches']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('blue')
        sheet.write('B2', 'Team:', self.formats['team_input_label'])
        sheet.write('C2', int(self.teams[0]["team_number"]), self.formats['team_input'])
        sheet.data_validation('C2', {
            'validate': 'list',
            'source':   '=team_number_list'
        })
        sheet.set_default_row(16, True)
        sheet.set_row(3, 35)
        data_len = 20
        col = 'B'
        match_num_col = col
        for header in headers:
            options = {}
            if "hidden" in header.keys():
                options['hidden'] = header['hidden']
            sheet.set_column(self.get_col_range(col),
                             width=header['width'] if "width" in header.keys() else 8,
                             options=options)
            sheet.write(
                    self.get_cell(col, 4),
                    header['title'],
                    self.formats[header['header_format']] if 'format' in header.keys()
                    else self.formats['pretty_header']
            )
            if header['title'] in ['Red 1', 'Red 2', 'Red 3', 'Blue 1', 'Blue 2', 'Blue 3']:
                sheet.conditional_format(self.get_col_range(col, 5, data_len), {
                    'type':               'formula',
                    'criteria':           '{0}5=$C$2'.format(col),
                    'format': self.formats['bold']
                })
            for i in range(data_len):
                if header['title'] == 'Match':
                    match_num_col = col
                    sheet.write(
                            self.get_cell(col, 5),
                            "=TRANSPOSE(FILTER(team_schedule_matches, team_schedule_team_number=$C$2))",
                            self.formats[header['format']] if 'format' in header.keys()
                            else self.formats['pretty_data_cell']
                    )
                    for i in range(1, data_len):
                        sheet.write_blank(
                                self.get_cell(col, 5 + i),
                                "",
                                self.formats[header['format']] if 'format' in header.keys()
                                else self.formats['pretty_data_cell']
                        )
                else:
                    for i in range(data_len):
                        sheet.write(
                                self.get_cell(col, i + 5),
                                '=IFERROR(LOOKUP({0}, schedule_match_number, {1}))'.format(
                                        self.get_col_range(match_num_col),
                                        'schedule_{}'.format(header['key'])
                                ),
                                self.formats[header['format']] if 'format' in header.keys()
                                else self.formats['pretty_data_cell']
                        )
            if header['title'] == 'Red Score':
                sheet.conditional_format(self.get_col_range(col, 5, data_len), {
                    'type':               'formula',
                    'criteria':           '{0}5>{1}5'.format(col, self.next_col(col)),
                    'format': self.formats['bold']
                })
                sheet.conditional_format(self.get_col_range(self.next_col(col), 5, data_len), {
                    'type':               'formula',
                    'criteria':           '{0}5>{1}5'.format(self.next_col(col), col),
                    'format': self.formats['bold']
                })
            col = self.next_col(col)

    def draw_pretty_team_stats(self):
        page_name = self.page_names['team_stats']
        header_dict = {
            'raw': self.headers['raw'],
            'raw_calculated':  self.headers['raw_calculated'][3:]
        }
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('green')
        sheet.write('B1', 'Team:', self.formats['team_input_label'])
        sheet.write('C1', int(self.teams[0]["team_number"]), self.formats['team_input'])
        sheet.data_validation('C1', {
            'validate': 'list',
            'source':   '=team_number_list'
        })
        sheet.set_default_row(16, True)
        sheet.set_row(3, 70)
        data_len = 20
        col = 'A'
        for key, headers in header_dict.items():
            for header in headers:
                sheet.write(
                        self.get_cell(col, 4),
                        header['title'],
                        self.formats[header['header_format']] if 'header_format' in header.keys()
                        else self.formats['pretty_header']
                )
                options = {}
                if "hidden" in header.keys():
                    options['hidden'] = header['hidden']
                sheet.set_column(self.get_col_range(col), header['width'] if "width" in header.keys() else 8,
                                 options=options)

                sheet.write(
                        self.get_cell(col, 5),
                        "=IFERROR(LOOKUP($C1, analysis_team_number, analysis_{}{}))"
                            .format('' if key == 'raw' else 'calculated_', header['key']),
                        self.formats['pretty_avg_cell']
                )
                sheet.write(
                        self.get_cell(col, 6),
                        "=FILTER({0}_{1}, {0}_team_number=$C$1)".format(key, header['key']),
                        self.formats[header['format']] if 'format' in header.keys()
                        else self.formats['pretty_data_cell']
                )

                for i in range(1, data_len):
                    sheet.write(
                            self.get_cell(col, 6 + i),
                            "",
                            self.formats[header['format']] if 'format' in header.keys()
                            else self.formats['pretty_data_cell']
                    )

                if "scale" in header.keys():
                    sheet.conditional_format(self.get_col_range(col, 6, data_len), {
                        'type':     'cell',
                        'criteria': '=',
                        'value':    0,
                        'format':   self.formats[header['format']] if 'format' in header.keys()
                                    else self.formats['pretty_data_cell']
                    })
                    sheet.conditional_format(self.get_col_range(col, 6, data_len), self.range_formats[header['scale']])

                col = self.next_col(col)

    def draw_pretty_match_rundown(self):
        page_name = self.page_names['match_rundown']
        raw_header_dict = {
            'raw': self.headers['raw'],
            'raw_calculated':  self.headers['raw_calculated'][3:]
        }
        analysis_headers = self.headers['analysis']
        sheet = self.workbook.add_worksheet(page_name)
        sheet.set_tab_color('green')
        sheet.set_default_row(10, True)

        sheet.write('B2', 'Team:', self.formats['team_input_label'])
        sheet.write('C2', int(self.teams[0]["team_number"]), self.formats['team_input'])
        sheet.data_validation('C2', {
            'validate': 'list',
            'source':   '=team_number_list'
        })

        sheet.write('A1', '=FILTER(team_schedule_matches, team_schedule_team_number=C2)')
        sheet.set_row(0, None, None, {'hidden': True})
        sheet.write('D2', 'Match:', self.formats['team_input_label'])
        sheet.write('E2', '=A1', self.formats['team_input'])
        sheet.data_validation('E2', {
            'validate': 'list',
            'source':   'A1:{}1'.format(self.next_col('A', 20))
        })

        col = 'A'
        row = 3
        team_num_col = col
        sheet.set_row(row - 1, 70)
        for header in analysis_headers:
            sheet.write(
                    self.get_cell(col, row),
                    header['title'],
                    self.formats[header['header_format']] if 'header_format' in header.keys()
                    else self.formats['pretty_header']
            )
            sheet.set_column(self.get_col_range(col), 8)
            if header['key'] == 'team_number':
                team_num_col = col
                for pos in range(6):
                    sheet.set_row(row + 1 + pos, 16)
                    sheet.write(
                            self.get_cell(col, row + 1 + pos),
                            "=LOOKUP($E$2, schedule_match_number, schedule_{}_{})".format('red' if pos < 3 else 'blue',
                                                                                          (pos % 3) + 1),
                            self.formats['red_alliance_data_cell' if pos < 3 else 'blue_alliance_data_cell']
                    )
                    sheet.conditional_format(
                        self.get_range(start_col=col, end_col=self.next_col(col, len(analysis_headers)),
                                       start_row=row + 1 + pos), {
                            'type':               'formula',
                            'criteria':           '${0}{1}=$C$2'.format(col, row + 1 + pos),
                            'format': self.formats['bold']
                        })
            else:
                for pos in range(6):
                    sheet.write(
                            self.get_cell(col, row + 1 + pos),
                            "=LOOKUP({}{}, analysis_team_number, analysis_{})".format(team_num_col, row + 1 + pos,
                                                                                      header['key']),
                            self.formats['red_alliance_data_cell' if pos < 3 else 'blue_alliance_data_cell']
                    )

            col = self.next_col(col)

        col = 'A'
        row = 11
        team_num_col = col
        sheet.set_row(row - 1, 70)
        for key, raw_headers in raw_header_dict.items():
            for header in raw_headers:
                sheet.write(
                        self.get_cell(col, row),
                        header['title'],
                        self.formats[header['header_format']] if 'header_format' in header.keys() else self.formats[
                            'pretty_header']
                )
                sheet.set_column(self.get_col_range(col), 8)
                if header['key'] == 'team_number':
                    team_num_col = col
                    for pos in range(6):
                        sheet.set_row(row + 1 + pos, 16)
                        sheet.write(
                                self.get_cell(col, row + 1 + pos),
                                "=LOOKUP($E$2, schedule_match_number, schedule_{}_{})".format('red' if pos < 3 else 'blue',
                                                                                              (pos % 3) + 1),
                                self.formats['red_alliance_data_cell' if pos < 3 else 'blue_alliance_data_cell']
                        )
                        sheet.conditional_format(
                            self.get_range(start_col=col, end_col=self.next_col(col, len(raw_headers)),
                                           start_row=row + 1 + pos), {
                                'type':               'formula',
                                'criteria':           '${0}{1}=$C$2'.format(col, row + 1 + pos),
                                'format': self.formats['bold']
                            })
                else:
                    for pos in range(6):
                        sheet.write(
                                self.get_cell(col, row + 1 + pos),
                                "=FILTER({}_{}, raw_match=$E$2, raw_team_number=${}{})".format(key, header['key'], team_num_col, row + 1 + pos),
                                self.formats['red_alliance_data_cell' if pos < 3 else 'blue_alliance_data_cell']
                        )

                col = self.next_col(col)

    @staticmethod
    def col_to_num(col):
        return (26 * (len(col) - 1)) + (ord(col[-1]) - ord('A'))

    @staticmethod
    def get_range(start_col='A', end_col='Z', start_row=None, end_row=None):
        return "{0}{2}:{1}{3}".format(start_col, end_col, start_row if start_row is not None else "",
                                      (end_row if end_row is not None else start_row) if start_row is not None else "")

    @staticmethod
    def get_col_range(col, start=1, num=None):
        if not num:
            return '{0}:{0}'.format(col)
        return '{0}{1}:{0}{2}'.format(col, start, start + num)

    @staticmethod
    def get_cell(col, row):
        return '{0}{1}'.format(col, row)

    @staticmethod
    def _get_data(data, key):
        keys = key
        if type(key) is str:
            keys = []
            [[keys.append(e) for e in k.split(".")] for k in key.split(",")]
        val = data
        for k in keys:
            try:
                val = val[str(k).strip()]
            except Exception as ex:
                print(val.keys())
                raise ex
        return val

    @staticmethod
    def upload_to_google_drive(filename, upload_filename="Clooney.xlsx"):
        gauth = GoogleAuth()
        # Try to load saved client credentials
        gauth.LoadCredentialsFile("credentials.json")
        if gauth.credentials is None:
            # Authenticate if they're not there
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
        else:
            # Initialize the saved creds
            gauth.Authorize()
        # Save the current credentials to a file
        gauth.SaveCredentialsFile("credentials.json")

        drive = GoogleDrive(gauth)

        for file in drive.ListFile({'q': "'1Y20z_cAs780qNOm-hwXx0ork1dgIQJHb' in parents and trashed=false"}).GetList():
            if file['title'] == upload_filename:
                clooney_file = file
                clooney_file.FetchMetadata()
                break
        else:
            clooney_file = drive.CreateFile({
                'title': upload_filename, "parents": [
                    {"kind": "drive#fileLink", "id": '1Y20z_cAs780qNOm-hwXx0ork1dgIQJHb'}]
            })

        clooney_file.SetContentFile(filename)
        clooney_file.Upload({'convert': True})


if __name__ == "__main__":
    db = sqlite3.connect('/Users/kestin/db.sqlite')
    tba = TBA('GdZrQUIjmwMZ3XVS622b6aVCh8CLbowJkCs5BmjJl2vxNuWivLz3Sf3PaqULUiZW')
    filename = '/Users/kestin/Google Drive/Scouting/Clooney.xlsx'
    gen = SpreadsheetGenerator(db, tba)
    gen.create_spreadsheet_for_event('2018onham', filename=filename)
    gen.upload_to_google_drive(filename)
