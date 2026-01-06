from app.domain.ocr.assembly_bom_extractor import AssemblyBOMExtractor


def test_extract_components_from_text_table_7260023():
    table_text = """
1
0615192
10
2
0910121
10
3
0910116
2
4
0670031
2
5
6
8349171
1
7
8
0614531
4
9
0910119
8
10
7340064
4
11
7261211
1
12
7261206
1
13
0314504
4
14
0852111
4
15
7261207
1
16
0670051
64
17
3837009
16
18
0816161
86
19
0670041
24
20
0670011
40
21
7261125
1
22
7261208
1
R1
R2
R3
""".strip()

    extractor = AssemblyBOMExtractor()
    comps = extractor.extract_components_from_text(table_text, root_item_no="7260023")
    got = [{"itemNo": c.item_no, "qty": c.qty, "position": c.position} for c in comps]

    expected = [
        {"itemNo": "0615192", "qty": 10, "position": "1"},
        {"itemNo": "0910121", "qty": 10, "position": "2"},
        {"itemNo": "0910116", "qty": 2, "position": "3"},
        {"itemNo": "0670031", "qty": 2, "position": "4"},
        {"itemNo": "8349171", "qty": 1, "position": "6"},
        {"itemNo": "0614531", "qty": 4, "position": "8"},
        {"itemNo": "0910119", "qty": 8, "position": "9"},
        {"itemNo": "7340064", "qty": 4, "position": "10"},
        {"itemNo": "7261211", "qty": 1, "position": "11"},
        {"itemNo": "7261206", "qty": 1, "position": "12"},
        {"itemNo": "0314504", "qty": 4, "position": "13"},
        {"itemNo": "0852111", "qty": 4, "position": "14"},
        {"itemNo": "7261207", "qty": 1, "position": "15"},
        {"itemNo": "0670051", "qty": 64, "position": "16"},
        {"itemNo": "3837009", "qty": 16, "position": "17"},
        {"itemNo": "0816161", "qty": 86, "position": "18"},
        {"itemNo": "0670041", "qty": 24, "position": "19"},
        {"itemNo": "0670011", "qty": 40, "position": "20"},
        {"itemNo": "7261125", "qty": 1, "position": "21"},
        {"itemNo": "7261208", "qty": 1, "position": "22"},
    ]

    assert got == expected


def test_extract_components_from_text_table_7260024_ignores_reference_rows_without_qty():
    table_text = """
1
7261213
1
2
7261215
1
3
7261214
1
4
7261045
1
5
7261216
1
6
7261108
1
7
7261107
1
8
7340224
1
9
0910119
4
10
7340064
2
11
0614531
2
12
0852111
4
13
0314504
4
14
0670011
32
15
3837011
12
16
0816161
64
17
0670041
64
18
0910116
2
19
0670031
2
20
0910121
10
21
0615192
10
R1
8349171
R2
7261046
R3
7261085
R4
7261025
""".strip()

    extractor = AssemblyBOMExtractor()
    comps = extractor.extract_components_from_text(table_text, root_item_no="7260024")
    got = [{"itemNo": c.item_no, "qty": c.qty, "position": c.position} for c in comps]

    expected = [
        {"itemNo": "7261213", "qty": 1, "position": "1"},
        {"itemNo": "7261215", "qty": 1, "position": "2"},
        {"itemNo": "7261214", "qty": 1, "position": "3"},
        {"itemNo": "7261045", "qty": 1, "position": "4"},
        {"itemNo": "7261216", "qty": 1, "position": "5"},
        {"itemNo": "7261108", "qty": 1, "position": "6"},
        {"itemNo": "7261107", "qty": 1, "position": "7"},
        {"itemNo": "7340224", "qty": 1, "position": "8"},
        {"itemNo": "0910119", "qty": 4, "position": "9"},
        {"itemNo": "7340064", "qty": 2, "position": "10"},
        {"itemNo": "0614531", "qty": 2, "position": "11"},
        {"itemNo": "0852111", "qty": 4, "position": "12"},
        {"itemNo": "0314504", "qty": 4, "position": "13"},
        {"itemNo": "0670011", "qty": 32, "position": "14"},
        {"itemNo": "3837011", "qty": 12, "position": "15"},
        {"itemNo": "0816161", "qty": 64, "position": "16"},
        {"itemNo": "0670041", "qty": 64, "position": "17"},
        {"itemNo": "0910116", "qty": 2, "position": "18"},
        {"itemNo": "0670031", "qty": 2, "position": "19"},
        {"itemNo": "0910121", "qty": 10, "position": "20"},
        {"itemNo": "0615192", "qty": 10, "position": "21"},
    ]

    assert got == expected


