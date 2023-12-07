from bs4 import BeautifulSoup
from ttf2web import TTF2Web
from os import path
    
def _get_unicode_string(char : chr, withU : bool = True) -> str:
    return ('U+' if withU else '') + hex(ord(char))[2:].upper().zfill(4) # eg U+1234

def get_used_characters_in_str(s : str) -> set[chr]:
    res : set[chr] = { " " } # Always contain space, otherwise no font file generated by TTF2Web 
    for c in s:
        res.add(c)
    return res

def get_used_characters_in_html(html : str) -> set[chr]:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return get_used_characters_in_str(text)

class charPair:
    def __init__(self, first : chr, second : chr):
        self.first = first
        self.second = second

    def __str__(self):
        return "[" + self.first + "-" + self.second + "]" # Pairs are inclusive
    
    # For print()-ing
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        if isinstance(other, charPair):
            return self.first == other.first and self.second == other.second
        return False
    
    def get_range(self):
        if self.first == self.second:
            return _get_unicode_string(self.first)
        else:
            return _get_unicode_string(self.first) + '-' + _get_unicode_string(self.second, False) # Eg "U+0061-0071"


# Taking a sorted list of characters, find the sequential subsets and return pairs of the start and end
# of each sequential subset
def _get_char_ranges(chars : list[chr]):
    chars.sort()
    if not chars:
        return []
    res : list[charPair] = []
    first : chr = chars[0]
    prev_seen : chr = first
    for c in chars[1:]:
        expected_next_char = chr(ord(prev_seen) + 1)
        if c != expected_next_char:
            # non-sequential, so time to start a new set
            pair = charPair(first, prev_seen)
            res.append(pair)
            first = c
        prev_seen = c
    # add final set if it hasn't been added yet
    if (not res) or (res[-1].second != prev_seen):
        pair = charPair(first, prev_seen)
        res.append(pair)

    return res

# Get the total size of multiple files (used for calculating font file sizes)
def _get_file_size_sum(files: list[str]) -> str:
    sum = 0
    for f in files:
        sum = sum + path.getsize(f)
    return sum
    
# Convert to human-readable size in MB or KB
def _file_size_to_readable(size : int) -> str:
    return str(round(size / 1024)) + "KB" if size < 1024 * 1024 else str(round(size / (1024 * 1024), 1)) + "MB" # nKB or n.nMB

# Takes the input text, and the fonts, and generates new font files
# Other methods (eg taking HTML files, or multiple pieces of text) all end up here
def optimise_fonts(text : str, fonts : list[str], fontpath : str = "", subsetname = "FontimizeSubset", verbose : bool = False) -> dict[str, str]:
    verbosity = 2 if verbose else 0 # tt2web has 0, 1, 2, so match that to off and on

    characters = get_used_characters_in_str(text)

    char_list = list(characters)
    if verbosity >= 2:
        print("Characters:")
        print("  " + str(char_list))

    char_ranges = _get_char_ranges(char_list)
    if verbosity >= 2:
        print("Character ranges:")
        print("  " + str(char_ranges))
    
    uranges = [[subsetname, ', '.join(r.get_range() for r in char_ranges)]] # subsetname here will be in the generated font, eg 'Arial.FontimizeSubset.woff'
    if verbosity >= 2:
        print("Unicode ranges:")
        print("  " + str(uranges))    

    res : dict[str, str] = {}
    # For each font, generate a new font file using only the used characters
    # By default, place it in the same folder as the respective font, unless fontpath is specified
    for font in fonts:
        assetdir = fontpath if fontpath else path.dirname(font)
        t2w = TTF2Web(font, uranges, assetdir=assetdir)
        woff2_list = t2w.generateWoff2(verbosity=verbosity)
        # print(woff2_list)
        assert len(woff2_list) == 1 # We only expect one font file to be generated, per font input
        assert len(woff2_list[0]) == 2 # Pair of font, plus ranges -- we only care about [0], the font
        res[font] = woff2_list[0][0]

    if verbosity >= 2:
        print("Generated the following fonts from the originals:")
        for k in res.keys():
            print("  " + k + " -> " + res[k])

    if verbosity >= 2:
        print("Results:")
        print("  Fonts processed: " + str(len(res)))
        sum_orig =  _get_file_size_sum(list(res.keys()))
        sum_new = _get_file_size_sum(list(res.values())) 
        print("  Total original font size: " + _file_size_to_readable(sum_orig))
        print("  Total optimised font size: " + _file_size_to_readable(sum_new))
        savings = sum_orig - sum_new;
        savings_percent = savings / sum_orig * 100 
        print("  Savings: " +  _file_size_to_readable(savings) + " less, which is " + str(round(savings_percent, 1)) + "%!")
        print("Done. Thankyou for using Fontimize!") # A play on Font and Optimise, haha, so good pun clever. But seriously - hopefully a memorable name!

    # Return a dict of input font file -> output font file, eg for CSS to be updated
    return res


def optimise_fonts_for_multiple_text(texts : list[str], fonts : list[str], fontpath : str = "", subsetname = "FontimizeSubset", verbose : bool = False) -> dict[str, str]:
    text = ""
    for t in texts:
        text = text + t
    return optimise_fonts(text, fonts, fontpath, verbose)

def optimise_fonts_for_html_contents(html_contents : list[str], fonts : list[str], fontpath : str = "", subsetname = "FontimizeSubset", verbose : bool = False) -> dict[str, str]:
    text = ""
    for html in html_contents:
        soup = BeautifulSoup(html, 'html.parser')
        text = text + soup.get_text()
    return optimise_fonts(text, fonts, fontpath, verbose)

def optimise_fonts_for_html_files(html_files : list[str], fonts : list[str], fontpath : str = "", subsetname = "FontimizeSubset", verbose : bool = False, rewriteCSS : bool = False) -> dict[str, str]:
    pass

# Note that unit tests for this file are in tests.py; run that file to run the tests
if __name__ == '__main__':
    generated = optimise_fonts("Hello world",
                               ['fonts/text/EB_Garamond/EBGaramond-VariableFont_wght.ttf', 'fonts/text/EB_Garamond/EBGaramond-Italic-VariableFont_wght.ttf'],
                               fontpath='',
                               verbose=True)

    # print("Not intended to be run; import this library")
    # assert False
    
    # print("Example usage:")

    # characters : set[chr] = get_used_characters_in_str("Helloworld")
    # characters = characters.union(get_used_characters_in_str("abcdefABCDEF.Z?<>,...+="))

    # char_list = list(characters)
    # char_list.sort()

    # char_ranges = _get_char_ranges(char_list)

    # print("Characters!")
    # print(char_list)

    # print("")
    # print("Ranges!")
    # print(char_ranges)

    # for r in char_ranges:
    #     print(r.get_range())

    # print("uranges")
    # uranges = [['subset', ', '.join(r.get_range() for r in char_ranges)]] # name here, "subset", will be in the generated font
    # print(uranges)

    # verbose = 2
    # fonts : list[str] = ['fonts/text/EB_Garamond/EBGaramond-VariableFont_wght.ttf', 'fonts/text/EB_Garamond/EBGaramond-Italic-VariableFont_wght.ttf']
    # for fontfile in fonts:
    #     verbosity = 2 if verbose else 1

    #     t2w = TTF2Web(fontfile, uranges, assetdir='output_temp')
    #     woff2_list = t2w.generateWoff2(verbosity=verbosity)
    #     #t2w.generateCss(woff2_list, verbosity=verbosity)





