#! /usr/bin/env python

import sys
import json
import random
import dendropy
from dendropy.test.support import pathmap
if sys.hexversion < 0x03040000:
    from dendropy.utility.filesys import pre_py34_open as open
from dendropy.utility.messaging import get_logger
_LOG = get_logger(__name__)

tree_file_titles = [
    'standard-test-trees-n14-unrooted-treeshapes',
    'standard-test-trees-n10-rooted-treeshapes',
    'standard-test-trees-n12-x2',
    'standard-test-trees-n33-x100a',
    'standard-test-trees-n33-x10a',
    'standard-test-trees-n33-x10b',
    'standard-test-trees-n33-annotated',
]

schema_extension_map = {
    "newick" : "newick",
    "nexus" : "nexus",
    "json" : "json",
}

tree_filepaths = {}
for schema in schema_extension_map:
    tree_filepaths[schema] = {}
    for tree_file_title in tree_file_titles:
        tf = "{}.{}".format(tree_file_title, schema_extension_map[schema])
        tree_filepaths[schema][tree_file_title] = pathmap.tree_source_path(tf)
tree_references = {}
for tree_file_title in tree_file_titles:
    with open(tree_filepaths["json"][tree_file_title]) as src:
        tree_references[tree_file_title] = json.load(src)

class StandardTestTreeChecker(object):

    def compare_annotations_to_json_metadata_dict(self,
            item,
            expected_metadata,
            coerce_metadata_values_to_string=False):
        item_annotations_as_dict = item.annotations.values_as_dict()
        if coerce_metadata_values_to_string:
            for k in expected_metadata:
                v = expected_metadata[k]
                if isinstance(v, list):
                    v = [str(i) for i in v]
                elif isinstance(v, tuple):
                    v = (str(i) for i in v)
                else:
                    v = str(v)
                expected_metadata[k] = v
        # for annote in item.annotations:
        #     print("{}: {}".format(annote.name, annote.value))
        # k1 = sorted(list(item_annotations_as_dict.keys()))
        # k2 = sorted(list(expected_metadata.keys()))
        # print("--")
        # for k in k1:
        #     print("'{}':'{}'".format(k, item_annotations_as_dict[k]))
        # print("--")
        # for k in k2:
        #     print("'{}':'{}'".format(k, expected_metadata[k]))
        # self.assertEqual(len(k1), len(k2))
        # self.assertEqual(set(k1), set(k2))
        # for key in set(item_annotations_as_dict.keys()):
        #     if item_annotations_as_dict[key] != expected_metadata[key]:
        #         v = expected_metadata[key]
        #         # if isinstance(v, list):
        #         #     print("{}: {}".format(v, [type(i) for i in v]))
        #         # elif isinstance(v, tuple):
        #         #     print("{}: {}".format(v, (type(i) for i in v)))
        #         # else:
        #         #     print("{}: {}".format(v, type(v)))
        #         print("**** {}:\t\t{} ({}) \t\t{} ({})".format(
        #             key,
        #             item_annotations_as_dict[key],
        #             type(item_annotations_as_dict[key]),
        #             expected_metadata[key],
        #             type(expected_metadata[key]),
        #             ))
        self.assertEqual(item_annotations_as_dict, expected_metadata)

    def compare_metadata_annotations(self,
            item,
            check,
            coerce_metadata_values_to_string=False):
        expected_annotations = check["metadata"]
        self.compare_annotations_to_json_metadata_dict(
                item,
                expected_annotations,
                coerce_metadata_values_to_string=coerce_metadata_values_to_string)

    def compare_comments(self,
            item,
            check,
            metadata_extracted=False):
        check_comments = list(check["comments"])
        item_comments = list(item.comments)
        for comment in item.comments:
            try:
                check_comments.remove(comment)
            except ValueError:
                pass
            else:
                item_comments.remove(comment)
        self.assertEqual(check_comments, [])
        if metadata_extracted:
            self.assertEqual(item_comments, [])
        else:
            for idx, c in enumerate(item_comments):
                if c.startswith("&"):
                    item_comments[idx] = c[1:]
            item_metadata_comments = ",".join(item_comments)
            check_metadata_comments = ",".join(check["metadata_comments"])
            self.maxDiff = None
            self.assertEqual(item_metadata_comments, check_metadata_comments)

    def label_nodes(self, tree):
        for node_idx, node in enumerate(tree):
            if node.taxon is not None:
                node.canonical_label = node.taxon.label
            else:
                node.canonical_label = node.label

    def compare_to_check_tree(self,
            tree,
            tree_file_title,
            check_tree_idx,
            suppress_internal_node_taxa=True,
            suppress_leaf_node_taxa=False,
            metadata_extracted=False,
            coerce_metadata_values_to_string=False,
            distinct_nodes_and_edges=True,
            taxa_on_tree_equal_taxa_in_taxon_namespace=False):
        check_tree = tree_references[tree_file_title][str(check_tree_idx)]
        self.assertIs(tree.is_rooted, check_tree["is_rooted"])
        self.compare_comments(tree, check_tree, metadata_extracted)
        if metadata_extracted:
            self.compare_metadata_annotations(
                    item=tree,
                    check=check_tree,
                    coerce_metadata_values_to_string=coerce_metadata_values_to_string)
        seen_taxa = []
        node_labels = []
        edge_labels = []
        num_visited_nodes = 0
        self.label_nodes(tree)
        for node_idx, node in enumerate(tree):
            num_visited_nodes += 1
            check_node = check_tree["nodes"][node.canonical_label]
            check_node_label = check_node["label"]
            self.assertEqual(node.canonical_label, check_node_label)
            # node_labels.append(node.canonical_label)
            _LOG.debug("{}: {}: {}".format(tree_file_title, check_tree_idx, node.canonical_label))

            check_node_children = check_node["children"]
            if check_node_children:
                self.assertTrue(node.is_internal())
                self.assertFalse(node.is_leaf())
                self.assertEqual(len(node._child_nodes), len(check_node_children))
                if suppress_internal_node_taxa:
                    self.assertEqual(node.label, check_node_label)
                    self.assertIs(node.taxon, None)
                    node_labels.append(node.label)
                else:
                    self.assertIsNot(node.taxon, None)
                    self.assertEqual(node.taxon.label, check_node_label)
                    self.assertIs(node.label, None)
                    seen_taxa.append(node.taxon)
            else:
                self.assertFalse(node.is_internal())
                self.assertTrue(node.is_leaf())
                self.assertEqual(len(node._child_nodes), len(check_node_children))
                if suppress_leaf_node_taxa:
                    self.assertEqual(node.label, check_node_label)
                    self.assertIs(node.taxon, None)
                    node_labels.append(node.label)
                else:
                    self.assertIsNot(node.taxon, None)
                    self.assertEqual(node.taxon.label, check_node_label)
                    self.assertIs(node.label, None)
                    seen_taxa.append(node.taxon)

            if node.parent_node is not None:
                if node.parent_node.is_internal:
                    if suppress_internal_node_taxa:
                        self.assertEqual(node.parent_node.label, check_node["parent"])
                        self.assertIs(node.parent_node.taxon, None)
                    else:
                        self.assertEqual(node.parent_node.taxon.label, check_node["parent"])
                        self.assertIs(node.parent_node.label, None)
                else:
                    if suppress_leaf_node_taxa:
                        self.assertEqual(node.parent_node.label, check_node["parent"])
                        self.assertIs(node.parent_node.taxon, None)
                    else:
                        self.assertEqual(node.parent_node.taxon.label, check_node["parent"])
                        self.assertIs(node.parent_node.label, None)
            else:
                self.assertEqual(check_node["parent"], "None")

            child_labels = []
            for ch in node.child_node_iter():
                if ch.is_internal():
                    if suppress_internal_node_taxa:
                        self.assertIs(ch.taxon, None)
                        child_labels.append(ch.label)
                    else:
                        self.assertIsNot(ch.taxon, None)
                        child_labels.append(ch.taxon.label)
                        self.assertIs(ch.label, None)
                else:
                    if suppress_leaf_node_taxa:
                        self.assertIs(ch.taxon, None)
                        child_labels.append(ch.label)
                    else:
                        self.assertIsNot(ch.taxon, None)
                        child_labels.append(ch.taxon.label)
                        self.assertIs(ch.label, None)
            self.assertEqual(len(child_labels), len(check_node["children"]))
            self.assertEqual(set(child_labels), set(check_node["children"]))

            edge = node.edge
            check_edge = check_tree["edges"][node.canonical_label]
            if edge.tail_node is None:
                self.assertEqual(check_edge["tail_node"], "None")
            else:
                self.assertEqual(edge.tail_node.canonical_label, check_edge["tail_node"])
            self.assertEqual(edge.head_node.canonical_label, check_edge["head_node"])
            self.assertAlmostEqual(node.edge.length, float(check_edge["length"]))

            # This hackery because NEWICK/NEXUS cannot distinguish between
            # node and edge comments, and everything gets lumped in as a
            # node comment
            if not distinct_nodes_and_edges:
                node.comments += edge.comments
                d = {
                        "comments": check_node["comments"] + check_edge["comments"],
                        "metadata_comments": check_node["metadata_comments"] + check_edge["metadata_comments"],
                        }
                self.compare_comments(node, d, metadata_extracted)
                if metadata_extracted:
                    obs_tuples = []
                    for o in (node, edge):
                        for a in o.annotations:
                            # print("++ {}: {} = {} ({})".format(type(o), a.name, a.value, type(a.value)))
                            v = a.value
                            if isinstance(v, list):
                                v = tuple(v)
                            obs_tuples.append( (a.name, v) )
                    exp_tuples = []
                    for idx, o in enumerate((check_node["metadata"], check_edge["metadata"])):
                        for k in o:
                            v = o[k]
                            # print("-- {}{}: {} = {}".format(type(o), idx+1, k, v))
                            if isinstance(v, list):
                                if coerce_metadata_values_to_string:
                                    v = tuple(str(vx) for vx in v)
                                else:
                                    v = tuple(v)
                            elif coerce_metadata_values_to_string:
                                v = str(v)
                            # print("-- {}{}: {} = {} ({})".format(type(o), idx+1, k, v, type(v)))
                            exp_tuples.append( (k, v) )
                    self.assertEqualUnorderedSequences(tuple(obs_tuples), tuple(exp_tuples))
            else:
                self.compare_comments(node, check_node, metadata_extracted)
                self.compare_comments(edge, check_edge, metadata_extracted)
                if metadata_extracted:
                    self.compare_metadata_annotations(
                            item=node,
                            check=check_node,
                            coerce_metadata_values_to_string=coerce_metadata_values_to_string)
                    self.compare_metadata_annotations(
                            item=edge,
                            check=check_edge,
                            coerce_metadata_values_to_string=coerce_metadata_values_to_string)

        self.assertEqual(num_visited_nodes, len(check_tree["nodeset"]))
        if taxa_on_tree_equal_taxa_in_taxon_namespace:
            self.assertEqual(len(seen_taxa), len(tree.taxon_namespace))
            self.assertEqual(set(seen_taxa), set(tree.taxon_namespace))
            node_labels.extend([t.label for t in tree.taxon_namespace])
        else:
            # node labels may have been interpreted as taxa depending on read mode
            node_labels.extend([t.label for t in tree.taxon_namespace if t.label not in node_labels])
        self.assertEqual(len(node_labels), len(check_tree["nodeset"]))
        self.assertEqual(set(node_labels), set(check_tree["nodeset"]))

    def verify_standard_trees(self,
            tree_list,
            tree_file_title,
            tree_offset=0,
            suppress_internal_node_taxa=True,
            suppress_leaf_node_taxa=False,
            metadata_extracted=False,
            coerce_metadata_values_to_string=False,
            distinct_nodes_and_edges=True,
            taxa_on_tree_equal_taxa_in_taxon_namespace=False):
        tree_reference = tree_references[tree_file_title]
        expected_number_of_trees = tree_reference["num_trees"]
        if tree_offset < 0:
            if abs(tree_offset) > expected_number_of_trees:
                tree_offset = 0
            else:
                tree_offset = expected_number_of_trees + tree_offset
        self.assertEqual(len(tree_list), expected_number_of_trees-tree_offset)
        # for tree_idx, (tree, check_tree) in enumerate(zip(tree_list, tree_directory[tree_file_title])):
        for tree_idx, tree in enumerate(tree_list):
            _LOG.debug("{}: {}".format(tree_file_title, tree_idx))
            self.assertIs(tree.taxon_namespace, tree_list.taxon_namespace)
            self.compare_to_check_tree(
                    tree=tree,
                    tree_file_title=tree_file_title,
                    check_tree_idx=tree_idx + tree_offset,
                    suppress_internal_node_taxa=suppress_internal_node_taxa,
                    suppress_leaf_node_taxa=suppress_leaf_node_taxa,
                    metadata_extracted=metadata_extracted,
                    coerce_metadata_values_to_string=coerce_metadata_values_to_string,
                    distinct_nodes_and_edges=distinct_nodes_and_edges,
                    taxa_on_tree_equal_taxa_in_taxon_namespace=taxa_on_tree_equal_taxa_in_taxon_namespace)

class StandardTreeListReaderTestCase(
        StandardTestTreeChecker):

    @classmethod
    def build(cls,
            schema,
            taxa_on_tree_equal_taxa_in_taxon_namespace):
        cls.schema = schema
        cls.schema_tree_filepaths = dict(tree_filepaths[cls.schema])
        cls.taxa_on_tree_equal_taxa_in_taxon_namespace = taxa_on_tree_equal_taxa_in_taxon_namespace

    def test_default_get(self):
        for tree_file_title in [
                'standard-test-trees-n14-unrooted-treeshapes',
                'standard-test-trees-n10-rooted-treeshapes',
                ]:
            tree_filepath = self.schema_tree_filepaths[tree_file_title]
            with open(tree_filepath, "r") as src:
                tree_string = src.read()
            with open(tree_filepath, "r") as tree_stream:
                approaches = (
                        (dendropy.TreeList.get_from_path, tree_filepath),
                        (dendropy.TreeList.get_from_stream, tree_stream),
                        (dendropy.TreeList.get_from_string, tree_string),
                        )
                for method, src in approaches:
                    tree_list = method(src, self.__class__.schema)
                    self.verify_standard_trees(
                            tree_list=tree_list,
                            tree_file_title=tree_file_title,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False,
                            metadata_extracted=False,
                            distinct_nodes_and_edges=False,
                            taxa_on_tree_equal_taxa_in_taxon_namespace=True)

    def test_default_read(self):
        preloaded_tree_file_title = "standard-test-trees-n33-x10a"
        preloaded_tree_reference = tree_references[preloaded_tree_file_title]
        tree_file_title = "standard-test-trees-n33-x10a"
        tree_reference = tree_references[tree_file_title]
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    ("read_from_path", tree_filepath),
                    ("read_from_stream", tree_stream),
                    ("read_from_string", tree_string),
                    )
            for method, src in approaches:
                # prepopulate
                tree_list = dendropy.TreeList.get_from_path(
                        self.schema_tree_filepaths[preloaded_tree_file_title],
                        self.__class__.schema)
                # check to make sure trees were loaded
                old_len = len(tree_list)
                self.assertEqual(old_len, len(tree_list._trees))
                self.assertEqual(old_len, preloaded_tree_reference["num_trees"])
                self.verify_standard_trees(
                        tree_list,
                        preloaded_tree_file_title,
                        distinct_nodes_and_edges=False,
                        taxa_on_tree_equal_taxa_in_taxon_namespace=True)

                # load
                old_id = id(tree_list)
                f = getattr(tree_list, method)
                trees_read = f(src, self.__class__.schema)
                new_id = id(tree_list)
                self.assertEqual(old_id, new_id)

                # make sure new trees added
                new_len = len(tree_list)
                self.assertEqual(new_len, len(tree_list._trees))
                expected_number_of_trees = tree_reference["num_trees"]
                self.assertEqual(old_len + expected_number_of_trees, new_len)
                self.assertEqual(trees_read, expected_number_of_trees)

                # check new trees
                for tree_idx, tree in enumerate(tree_list[old_len:]):
                    self.compare_to_check_tree(
                            tree=tree,
                            tree_file_title=tree_file_title,
                            check_tree_idx=tree_idx,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False,
                            metadata_extracted=False,
                            distinct_nodes_and_edges=False,
                            taxa_on_tree_equal_taxa_in_taxon_namespace=True)

                # make sure old ones still intact
                for tree_idx, tree in enumerate(tree_list[:old_len]):
                    self.compare_to_check_tree(
                            tree=tree,
                            tree_file_title=preloaded_tree_file_title,
                            check_tree_idx=tree_idx,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False,
                            metadata_extracted=False,
                            distinct_nodes_and_edges=False,
                            taxa_on_tree_equal_taxa_in_taxon_namespace=True)

    def test_selective_taxa_get(self):
        # skip big files
        tree_file_title = "standard-test-trees-n12-x2"
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        for suppress_internal_node_taxa in [True, False]:
            for suppress_leaf_node_taxa in [True, False]:
                kwargs = {
                        "suppress_internal_node_taxa": suppress_internal_node_taxa,
                        "suppress_leaf_node_taxa": suppress_leaf_node_taxa,
                }
                with open(tree_filepath, "r") as tree_stream:
                    approaches = (
                            (dendropy.TreeList.get_from_path, tree_filepath),
                            (dendropy.TreeList.get_from_stream, tree_stream),
                            (dendropy.TreeList.get_from_string, tree_string),
                            )
                    for method, src in approaches:
                        tree_list = method(src, self.__class__.schema, **kwargs)
                        self.verify_standard_trees(
                                tree_list=tree_list,
                                tree_file_title=tree_file_title,
                                suppress_internal_node_taxa=suppress_internal_node_taxa,
                                suppress_leaf_node_taxa=suppress_leaf_node_taxa,
                                metadata_extracted=False,
                                distinct_nodes_and_edges=False,
                                taxa_on_tree_equal_taxa_in_taxon_namespace=self.__class__.taxa_on_tree_equal_taxa_in_taxon_namespace)

    def test_selective_taxa_read(self):
        # skip big files
        tree_file_title = "standard-test-trees-n12-x2"
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        for suppress_internal_node_taxa in [True, False]:
            for suppress_leaf_node_taxa in [True, False]:
                kwargs = {
                        "suppress_internal_node_taxa": suppress_internal_node_taxa,
                        "suppress_leaf_node_taxa": suppress_leaf_node_taxa,
                }
                with open(tree_filepath, "r") as tree_stream:
                    approaches = (
                            ("read_from_path", tree_filepath),
                            ("read_from_stream", tree_stream),
                            ("read_from_string", tree_string),
                            )
                    for method, src in approaches:
                        tree_list = dendropy.TreeList()
                        old_id = id(tree_list)
                        f = getattr(tree_list, method)
                        f(src, self.__class__.schema, **kwargs)
                        new_id = id(tree_list)
                        self.verify_standard_trees(
                                tree_list=tree_list,
                                tree_file_title=tree_file_title,
                                suppress_internal_node_taxa=suppress_internal_node_taxa,
                                suppress_leaf_node_taxa=suppress_leaf_node_taxa,
                                metadata_extracted=False,
                                distinct_nodes_and_edges=False,
                                taxa_on_tree_equal_taxa_in_taxon_namespace=self.__class__.taxa_on_tree_equal_taxa_in_taxon_namespace)

    def test_tree_offset_get(self):
        tree_file_title = "standard-test-trees-n33-x100a"
        tree_reference = tree_references[tree_file_title]
        expected_number_of_trees = tree_reference["num_trees"]
        tree_offsets = set([0, expected_number_of_trees-1, -1, -expected_number_of_trees])
        while len(tree_offsets) < 8:
            tree_offsets.add(random.randint(1, expected_number_of_trees-2))
        while len(tree_offsets) < 12:
            tree_offsets.add(random.randint(-expected_number_of_trees-2, -2))
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        for tree_offset in tree_offsets:
            with open(tree_filepath, "r") as tree_stream:
                approaches = (
                        (dendropy.TreeList.get_from_path, tree_filepath),
                        (dendropy.TreeList.get_from_stream, tree_stream),
                        (dendropy.TreeList.get_from_string, tree_string),
                        )
                for method, src in approaches:
                    tree_list = method(
                            src,
                            self.__class__.schema,
                            collection_offset=0,
                            tree_offset=tree_offset,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False)
                    self.verify_standard_trees(
                            tree_list=tree_list,
                            tree_file_title=tree_file_title,
                            tree_offset=tree_offset,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False,
                            distinct_nodes_and_edges=False,
                            taxa_on_tree_equal_taxa_in_taxon_namespace=True)

    def test_tree_offset_read(self):
        tree_file_title = "standard-test-trees-n33-x100a"
        tree_reference = tree_references[tree_file_title]
        expected_number_of_trees = tree_reference["num_trees"]
        tree_offsets = set([0, expected_number_of_trees-1, -1, -expected_number_of_trees])
        while len(tree_offsets) < 8:
            tree_offsets.add(random.randint(1, expected_number_of_trees-2))
        while len(tree_offsets) < 12:
            tree_offsets.add(random.randint(-expected_number_of_trees-2, -2))
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        for tree_offset in tree_offsets:
            with open(tree_filepath, "r") as tree_stream:
                approaches = (
                        ("read_from_path", tree_filepath),
                        ("read_from_stream", tree_stream),
                        ("read_from_string", tree_string),
                        )
                for method, src in approaches:
                    tree_list = dendropy.TreeList()
                    f = getattr(tree_list, method)
                    trees_read = f(src,
                            self.__class__.schema,
                            collection_offset=0,
                            tree_offset=tree_offset,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False)
                    self.verify_standard_trees(
                            tree_list=tree_list,
                            tree_file_title=tree_file_title,
                            tree_offset=tree_offset,
                            suppress_internal_node_taxa=True,
                            suppress_leaf_node_taxa=False,
                            distinct_nodes_and_edges=False,
                            taxa_on_tree_equal_taxa_in_taxon_namespace=True)

    def test_tree_offset_without_collection_offset_get(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        approaches = (
                dendropy.TreeList.get_from_path,
                dendropy.TreeList.get_from_stream,
                dendropy.TreeList.get_from_string,
                )
        for approach in approaches:
            with self.assertRaises(TypeError):
                approach(tree_filepath, self.__class__.schema, collection_offset=None, tree_offset=0)

    def test_tree_offset_without_collection_offset_read(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        approaches = (
                "read_from_path",
                "read_from_stream",
                "read_from_string",
                )
        for approach in approaches:
            tree_list = dendropy.TreeList()
            f = getattr(tree_list, approach)
            with self.assertRaises(TypeError):
                f(tree_filepath, self.__class__.schema, collection_offset=None, tree_offset=0)

    def test_out_of_range_tree_offset_get(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        tree_reference = tree_references[tree_file_title]
        expected_number_of_trees = tree_reference["num_trees"]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    (dendropy.TreeList.get_from_path, tree_filepath),
                    (dendropy.TreeList.get_from_stream, tree_stream),
                    (dendropy.TreeList.get_from_string, tree_string),
                    )
            for method, src in approaches:
                with self.assertRaises(IndexError):
                    method(src, self.__class__.schema, collection_offset=0, tree_offset=expected_number_of_trees)

    def test_out_of_range_tree_offset_read(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        tree_reference = tree_references[tree_file_title]
        expected_number_of_trees = tree_reference["num_trees"]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    ("read_from_path", tree_filepath),
                    ("read_from_stream", tree_stream),
                    ("read_from_string", tree_string),
                    )
            for method, src in approaches:
                tree_list = dendropy.TreeList()
                f = getattr(tree_list, method)
                with self.assertRaises(IndexError):
                    f(src, self.__class__.schema, collection_offset=0, tree_offset=expected_number_of_trees)

    def test_out_of_range_collection_offset_get(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    (dendropy.TreeList.get_from_path, tree_filepath),
                    (dendropy.TreeList.get_from_stream, tree_stream),
                    (dendropy.TreeList.get_from_string, tree_string),
                    )
            for method, src in approaches:
                with self.assertRaises(IndexError):
                    method(src, self.__class__.schema, collection_offset=1, tree_offset=0)

    def test_out_of_range_collection_offset_read(self):
        tree_file_title = 'standard-test-trees-n33-x10a'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    ("read_from_path", tree_filepath),
                    ("read_from_stream", tree_stream),
                    ("read_from_string", tree_string),
                    )
            for method, src in approaches:
                tree_list = dendropy.TreeList()
                f = getattr(tree_list, method)
                with self.assertRaises(IndexError):
                    f(src, self.__class__.schema, collection_offset=1, tree_offset=0)

    def test_unsupported_keyword_arguments_get(self):
        tree_file_title = 'standard-test-trees-n12-x2'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    (dendropy.TreeList.get_from_path, tree_filepath),
                    (dendropy.TreeList.get_from_stream, tree_stream),
                    (dendropy.TreeList.get_from_string, tree_string),
                    )
            for method, src in approaches:
                with self.assertRaises(TypeError):
                    method(src,
                            self.__class__.schema,
                            suppress_internal_taxa=True,  # should be suppress_internal_node_taxa
                            gobbledegook=False,
                            )

    def test_unsupported_keyword_arguments_read(self):
        tree_file_title = 'standard-test-trees-n12-x2'
        tree_filepath = self.schema_tree_filepaths[tree_file_title]
        with open(tree_filepath, "r") as src:
            tree_string = src.read()
        with open(tree_filepath, "r") as tree_stream:
            approaches = (
                    ("read_from_path", tree_filepath),
                    ("read_from_stream", tree_stream),
                    ("read_from_string", tree_string),
                    )
            for method, src in approaches:
                tree_list = dendropy.TreeList()
                f = getattr(tree_list, method)
                with self.assertRaises(TypeError):
                    f(src,
                      self.__class__.schema,
                      suppress_internal_taxa=True,  # should be suppress_internal_node_taxa
                      gobbledegook=False,
                    )