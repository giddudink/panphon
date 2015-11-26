# -*- coding: utf-8 -*-
from __future__ import print_function
import pkg_resources
import regex as re
import unicodecsv as csv
import logging


logging.basicConfig(level=logging.DEBUG)


class FeatureError(Exception):
    pass


class SegmentError(Exception):
    pass


class IpaRegexError(Exception):
    pass


FT_REGEX = re.compile(ur'([-+0])([a-z][A-Za-z]*)', re.U | re.X)


SEG_REGEX = re.compile(ur'[\p{InBasic_Latin}\p{InGreek_and_Coptic}' +
                       ur'\p{InIPA_Extensions}œ\u00C0-\u00FF]' +
                       ur'[\u0300-\u0360\u0362-\u036F]*' +
                       ur'\p{InSpacing_Modifier_Letters}*',
                       re.U | re.X)


def segment_text(text, seg_regex=SEG_REGEX):
    """Return an iterator of segments in the text.

    text -- string of IPA Unicode text
    seg_regex -- compiled regex defining a segment (base + modifiers)
    """
    for m in seg_regex.finditer(text):
        yield m.group(0)


def fts(s):
    """Given string with +/-[alphabetical sequence]s, return list of features.

    s -- string with +/-[alphabetical sequence]s
    """
    return [m.groups() for m in FT_REGEX.finditer(s)]


filenames = {
    'spe+': 'data/segment_features.csv',
    'panphon': 'data/segment_features.csv',
}


class BoolTree(object):
    def __init__(self, test=None, t_node=None, f_node=None):
        self.test = test
        self.t_node = t_node
        self.f_node = f_node

    def get_value(self):
        logging.debug('t_node={} f_node={}'.format(self.t_node, self.f_node))
        if self.test:
            if isinstance(self.t_node, BoolTree):
                return self.t_node.get_value()
            else:
                logging.debug('Returning {}'.format(self.t_node))
                return self.t_node
        else:
            if isinstance(self.f_node, BoolTree):
                return self.f_node.get_value()
            else:
                logging.debug('Returning {}'.format(self.f_node))
                return self.f_node


class FeatureTable(object):
    """Encapsulate the segment <=> feature mapping in the file
    data/segment_features.csv.

    """

    def __init__(self, feature_set='spe+'):
        filename = filenames[feature_set]
        self._read_table(filename)
        # assert self.sonority(u'p') == 1
        # assert self.sonority(u'a') == 5
        # assert self.sonority(u'pʰ') == 1
        # assert self.sonority(u'ã') == 5

    def _read_table(self, filename):
        """Read the data from data/segment_features.csv into self.segments, a
        list of 2-tuples of unicode strings and sets of feature tuples and
        self.seg_dict, a dictionary mapping from unicode segments and sets of
        feature tuples.
        """
        filename = pkg_resources.resource_filename(
            __name__, filename)
        self.segments = []
        with open(filename, 'rb') as f:
            reader = csv.reader(f, encoding='utf-8')
            header = reader.next()
            names = header[1:]
            for row in reader:
                seg = row[0]
                vals = row[1:]
                specs = set(zip(vals, names))
                self.segments.append((seg, specs))
        self.seg_dict = dict(self.segments)
        self.names = names

    def delete_ties(self):
        """Deletes ties from all segments."""
        self.seg_dict = {k.replace(u'\u0361', u''): v
                         for (k, v) in self.seg_dict.items()}

    def fts(self, segment):
        """Returns features corresponding to segment as list of <feature,
        value> tuples."""
        if segment in self.seg_dict:
            return self.seg_dict[segment]
        else:
            raise SegmentError

    def match(self, ft_mask, ft_seg):
        """Evaluates whether a set of features (ft_mask) are a subset of another
        set of features (ft_seg).

        ft_mask -- pattern defined as set of features (<val, name> tuples).
        ft_seg -- segment defined as a set of features (<val, name> tuples).
        """
        return set(ft_mask) <= set(ft_seg)

    def fts_match(self, features, segment):
        """Evaluates whether a set of features 'match' a segment (are a subset
        of that segment's features); returns 'None' if segment is unknown.
        """
        features = set(features)
        if segment in self.seg_dict:
            return features <= self.seg_dict[segment]
        else:
            return None

    def seg_known(self, segment):
        """Returns True if segment is in segment <=> features database."""
        return segment in self.seg_dict

    def seg_fts(self, segment):
        """Returns the features as a list of 2-tuples, given a segment as a
        Unicode string; returns 'None' if segment is unknown.

        segment -- segment for which features are to be returned as
        Unicode string """
        if segment in self.seg_dict:
            return self.seg_dict[segment]
        else:
            return None

    def fts_intersection(self, segments):
        """Returns the features shared by all segments in the list/set of
        segments. Segments that are not known are ignored.

        segments -- set/list of features
        """
        segments = set([seg for seg
                        in segments
                        if seg in self.seg_dict])
        seg1 = segments.pop()
        fts = self.seg_dict[seg1]
        for seg in segments:
            fts = fts & self.seg_dict[seg]
        return fts

    def fts_match_any(self, fts, inv):
        """Returns a boolean based on whether there is a segment in 'inv'
        that matches all of the features in 'features'.

        features -- a collection of feature 2-tuples <val, name>
        inv -- a collection of segments represented as Unicode
               strings

        """
        return any([self.fts_match(fts, s) for s in inv])

    def fts_match_all(self, fts, inv):
        """Returns a boolean based on whether all segments in 'inv'
         matche all of the features in 'features'.

        features -- a collection of feature 2-tuples <val, name>
        inv -- a collection of segments represented as Unicode
               strings

        """
        return all([self.fts_match(fts, s) for s in inv])

    def seg_diff(self, seg1, seg2):
        """Return the features by which seg1 and seg2 differ.

        seg1, seg2 -- segments (lists of <value, name> pairs)
        """

        def seg_to_dict(seg):
            return {k: v for (v, k) in seg}

        assert seg_to_dict([(1, 2), (3, 4)]) == {1: 2, 3: 4}

    # Needs to be debugged or removed!
    def fts_to_str(self, seg):
        """Returns a string representation of a set of <feature, value>
        pairs."""
        vals = {u'0': ' ', u'-': '0', u'+': '1'}
        seg_dict = {n: v for (v, n) in seg}
        vector = []
        for name in self.names:
            if name in seg_dict:
                vector.append(vals[seg_dict[name]])
        return ''.join(vector)

    def fts_contrast(self, fs, ft_name, inv):
        """Return True if there is a segment in inv that contrasts in feature
        ft_name.

        ft_name -- name of the feature where contrast must be present.
        inv -- collection of segments represented as Unicode segments.
        """
        plus, minus = (u'+', ft_name), (u'-', ft_name)
        w_plus, w_minus = set(list(fs) + [plus]), set(list(fs) + [minus])
        return any([self.fts_match(w_plus, s) for s in inv]) and \
            any([self.fts_match(w_minus, s) for s in inv])

    def fts_count(self, fts, inv):
        """Returns the count of segments in an inventory matching a give
        feature mask.

        fts -- feature mask given as a set of <val, name> tuples
        inv -- inventory of segments (as Unicode IPA strings)
        """
        return len(filter(lambda s: self.fts_match(fts, s), inv))

    def sonority_from_fts(self, seg):
        def match(m):
            return self.match(fts(m), seg)
        minusHi = BoolTree(match('-hi'), 8, 7)
        plusLo = BoolTree(match('+lo'), 9, minusHi)
        minusNas = BoolTree(match('-nas'), 6, 5)
        plusVoi1 = BoolTree(match('+voi'), 4, 3)
        plusVoi2 = BoolTree(match('+voi'), 2, 1)
        plusCont = BoolTree(match('+cont'), plusVoi1, plusVoi2)
        plusSon = BoolTree(match('+son'), minusNas, plusCont)
        minusCons = BoolTree(match('-cons'), plusLo, plusSon)
        return minusCons.get_value()

    def sonority(self, seg):
        """Returns the sonority of a segment.

        seg -- segment given as a Unicode IPA string
        """
        return self.sonority_from_fts(self.fts(seg))

    def all_segs_matching_fts(self, fts):
        """Return a segments matching a feature mask, both as <name, value>
        tuples (sorted in reverse order by length).

         fts -- feature mask as <name, value> tuples.
        """
        matching_segs = []
        for seg, pairs in self.segments:
            if set(fts) <= set(pairs):
                matching_segs.append(seg)
        return sorted(matching_segs, reverse=True)

    def compile_regex_from_str(self, ft_str):
        """Given a string describing features masks for a sequence of segments,
        return a regex matching the corresponding strings.

        ft_str -- A string consisting of feature masks, each enclosed in
        square brackets, in which the features are delimited by any
        standard delimiter. """

        sequence = []
        for m in re.finditer(ur'\[([^]]+)\]', ft_str):
            ft_mask = fts(m.group(1))
            segs = self.all_segs_matching_fts(ft_mask)
            sub_pat = u'({})'.format(u'|'.join(segs))
            sequence.append(sub_pat)
        pattern = u''.join(sequence)
        regex = re.compile(pattern)
        return regex