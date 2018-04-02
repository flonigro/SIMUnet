# -*- coding: utf-8 -*-
"""
Utilities for loading data from fit folders
"""
import logging
from collections import namedtuple
from io import StringIO
import pathlib

import numpy as np
import pandas as pd
from reportengine.compat import yaml

from reportengine import collect
from reportengine.table import table
from reportengine.checks import make_argcheck, CheckError
from reportengine.compat import yaml

from validphys.core import PDF
from validphys import checks
from validphys.plotoptions import get_info
from validphys import sumrules

#TODO: Add more stuff here as needed for postfit
LITERAL_FILES = ['chi2exps.log']
REPLICA_FILES = ['.dat', '.fitinfo', '.params', '.preproc', '.sumrules']

#t = blessings.Terminal()
log = logging.getLogger(__name__)

#TODO setup make_check on these
def check_nnfit_results_path(path):
    """ Returns True if the requested path is a valid results directory,
    i.e if it is a directory and has a 'nnfit' subdirectory"""
    if not path.is_dir():
        log.warn('Path is not a directory %s' % path)
        return False
    if not (path / 'nnfit').is_dir():
        log.warn('Path %s is not a directory' % (str(path/'nnfit')))
        return False
    return True

def check_lhapdf_info(results_dir, fitname):
    """ Check that an LHAPDF info metadata file is
    present in the fit results """
    info_path = results_dir.joinpath('nnfit', '%s.info' % fitname)
    if not info_path.is_file():
        log.warn('Cannot find info file at %s' % info_path)
        return False
    return True

#TODO This should establish if the .dat files are corrupted or not
def check_replica_files(replica_path, prefix):
    """ Verification of a replica results directory at `replica_path`
    for a fit named `prefix`. Returns True if the results
    directory is complete"""

    path = pathlib.Path(replica_path)
    if not path.is_dir():
        log.warn("Invalid directory for replica %s" % path)
        return False
    valid = True
    for f in LITERAL_FILES:
        test_path = path/f
        if not test_path.is_file():
            log.warn("Missing file: %s" % test_path)
            valid = False
    for f in REPLICA_FILES:
        test_path = (path/prefix).with_suffix(f)
        if not test_path.is_file():
            log.warn("Missing file: %s" % test_path)
            valid = False
    if not valid:
        log.warn("Found invalid replica %s" % path)
    return valid

FitInfo = namedtuple("FitInfo", ("nite", 'training', 'validation', 'chi2', 'is_positive', 'arclengths'))
def load_fitinfo(replica_path, prefix):
    """Process the data in the ".fitinfo" file of a single replica."""
    p = replica_path / (prefix + '.fitinfo')
    with open(p, 'r') as fitinfo_file:
        fitinfo_line = fitinfo_file.readline().split() # General fit properties
        fitinfo_arcl = fitinfo_file.readline()         # Replica arc-lengths

        n_iterations   = int(  fitinfo_line[0])
        erf_validation = float(fitinfo_line[1])
        erf_training   = float(fitinfo_line[2])
        chisquared     = float(fitinfo_line[3])
        is_positive    = fitinfo_line[4] == "POS_PASS"
        arclengths     = np.fromstring(fitinfo_arcl, sep=' ')
    return FitInfo(n_iterations, erf_training, erf_validation, chisquared, is_positive, arclengths)


#TODO: Produce a more informative .sumrules file.
def load_sumrules(replica_path, prefix):
    """Load the values of the sum rules defined in
    ``validphys.pdfgrids.SUM_RULES`` from a given replica."""
    return np.loadtxt(replica_path/f'{prefix}.sumrules')[:len(sumrules.SUM_RULES)]

@checks.check_has_fitted_replicas
def replica_paths(fit):
    """Return the paths of all the replicas"""
    #Total number of members = number of replicas + 1
    l = len(PDF(fit.name))
    postfit_path     = fit.path / 'postfit'
    old_postfit_path = fit.path / 'nnfit'
    if postfit_path.is_dir():
        return [postfit_path / f'replica_{index}' for index in range(1, l)]
    return [old_postfit_path / f'replica_{index}' for index in range(1, l)]

def replica_data(fit, replica_paths):
    """Load the data from the fitinfo file of each of the replicas.
    The corresponding PDF set must be installed in the LHAPDF path.

    The included information is:

    ('nite', 'training', 'validation', 'chi2', 'pos_status', 'arclenghts')"""
    return [load_fitinfo(path, fit.name) for path in replica_paths]

def fit_sum_rules(fit, replica_paths):
    """Return a SumRulesGrid object with the sumrules for each replica as
    calculated by nnfit at the initial scale. This is the same object as
    the one produced by
    ``validphys.pdfgrids.sum_rules`` which is instead obtained from LHAPDF at
    a given energy"""
    res = np.zeros((len(sumrules.SUM_RULES),len(replica_paths)))
    for i, p in enumerate(replica_paths):
        res[:, i] = load_sumrules(p, fit.name)
    return sumrules.SumRulesGrid(*res)

@table
def fit_sum_rules_table(fit_sum_rules):
    return sumrules.sum_rules_table(fit_sum_rules)


fits_replica_data = collect('replica_data', ('fits',))

#Do collect in two parts so we get a list for each fit instead of a single list
all_datasets = collect('dataset', ('experiments', 'experiment'))
fits_datasets = collect('all_datasets', ('fits', 'fitinputcontext',))

@make_argcheck
def _assert_two_fits(fits):
    """Check that there are exatly two fits"""
    if len(fits) != 2:
        raise CheckError("Exactly two fits are required")

DatasetComp = namedtuple('DatasetComp', ('common', 'first_only', 'second_only'))

@_assert_two_fits
def match_datasets_by_name(fits, fits_datasets):
    """Return a tuple with common, first_only and second_only.
    The elements of the tuple are mappings where the keys are dataset names
    and the values are the two datasets contained in each fit for common, and
    the corresponfing dataset inclucded only in the first fit and only in the
    second fit."""

    firstds, secondds = [{ds.name: ds for ds in datasets} for datasets in fits_datasets]
    common_keys = firstds.keys() & secondds.keys()
    first_keys = firstds.keys() - secondds.keys()
    seccond_keys = secondds.keys() - firstds.keys()

    common = {k: (firstds[k], secondds[k]) for k in common_keys}
    first_only = {k: firstds[k] for k in first_keys}
    second_only = {k: secondds[k] for k in seccond_keys}
    return DatasetComp(common, first_only, second_only)


#TODO: Do we do md output here or that's for the templates?
def print_dataset_differences(fits, match_datasets_by_name,
                              print_common:bool=True):
    """Given exactly two fits, print the datasets that are included in one "
    "but not in the other. If `print_common` is True, also print the datasets
    that are common."""
    m = match_datasets_by_name
    first,second = fits
    res = StringIO()
    if m.common and print_common:
        res.write("The following datasets are included in both `%s` and `%s`:\n\n" % (first, second))
        for k,v in m.common.items():
            info = get_info(v[0].commondata)
            res.write(' - %s\n' % info.dataset_label)
        res.write('\n')
    if m.first_only:
        res.write("The following datasets are included in `%s` but not in `%s`:\n\n"% (first,second))
        for k,v in m.first_only.items():
            info = get_info(v.commondata)
            res.write(' - %s\n' % info.dataset_label)
        res.write('\n')
    if m.second_only:
        res.write("The following datasets are included in `%s` but not in `%s`:\n\n"% (second,first))
        for k,v in m.second_only.items():
            info = get_info(v.commondata)
            res.write(' - %s\n' % info.dataset_label)
        res.write('\n')
    return res.getvalue()

print_dataset_differences.highlight = 'markdown'

@_assert_two_fits
def test_for_same_cuts(fits, match_datasets_by_name):
    """Given two fits, return a list of tuples `(first, second)`
    where `first` and `second` are
    DatasetSpecs that correspond to the same dataset but have different cuts,
    such that `first` is included in the first fit and `second` in the second.
    """
    common = match_datasets_by_name.common
    first_fit, second_fit = fits
    res = []
    for ds, (first, second) in common.items():
        if first.cuts:
            c1 = first.cuts.load()
        else:
            c1 = ['Allpass']
        if second.cuts:
            c2 = second.cuts.load()
        else:
            c2 = ['Allpass']
        if not np.array_equal(c1, c2):
            msg = "Cuts for %s are not the same:\n%s:\n%s\n\n%s:\n%s" % (ds, first_fit, c1, second_fit, c2)
            log.info(msg)
            res.append((first,  second))
    return res

def print_different_cuts(fits, test_for_same_cuts):
    """Print a summary of the datasets that are included in both fits but have
    different cuts."""
    res = StringIO()
    first_fit, second_fit = fits
    if test_for_same_cuts:
        res.write("The following datasets are both included but have different kinematical cuts:\n\n")
        for (first, second) in test_for_same_cuts:
            info = get_info(first.commondata)
            total_points = len(first.commondata.load())
            res.write(" - %s:\n" % info.dataset_label)
            first_len = len(first.cuts.load()) if first.cuts else total_points
            second_len = len(second.cuts.load()) if second.cuts else total_points
            res.write("    * %s includes %d out of %d points.\n" % (first_fit, first_len, total_points))
            res.write("    * %s includes %d out of %d points.\n" % (second_fit, second_len, total_points))
        res.write('\n')


    return res.getvalue()

def _get_fitted_index(pdf, i):
    """Return the nnfit index for the replcia i"""
    p = pathlib.Path(pdf.infopath).with_name(f'{pdf.name}_{i:04d}.dat')
    with open(p) as f:
        it = yaml.safe_load_all(f)
        metadata = next(it)
    return metadata['FromMCReplica']

@make_argcheck
def _check_has_replica_tags(pdf):
    """Check that the PDF has fitted index tags."""
    try:
        _get_fitted_index(pdf,1)
    except KeyError as e:
        raise CheckError("PDF replica file don't contain "
                         "the fitted replica tag.") from e

@_check_has_replica_tags
def fitted_replica_indexes(pdf):
    """Return nnfit index of replicas 1 to N."""
    return [_get_fitted_index(pdf,i) for i in range(1, len(pdf))]

fits_replica_indexes =  collect('fitted_replica_indexes', ('fits','fitpdf'))

def fits_replica_data_correlated(fits_replica_data, fits_replica_indexes, fits):
    """Return a table with the same columns as ``replica_data`` indexed by the
    replica fit ID. For identical fits,
    the values across rows should be the same.

    If some replica ID is not present for a given fit (e.g. discarded by
    postfit), the corresponding entries in the table will be null.

    """
    dfs = []
    for dt, inds in zip(fits_replica_data, fits_replica_indexes):
        dfs.append(pd.DataFrame(dt, columns=FitInfo._fields, index=inds))
    return pd.concat(dfs, axis=1, keys=[fit.name for fit in fits])

@table
def datasets_properties_table(fit):
    """Returns table of dataset properties for each dataset used in a fit."""
    expmap = yaml.safe_load(open(fit.path/'filter.yml'))
    expmap_exps = expmap['experiments']
    expmap_datasets = [x['datasets'] for x in expmap_exps]
    list_of_datasets = [it for x in expmap_exps for it in x['datasets']]
    names = []
    tfs = []
    cfacs = []
    others = []
    for ele in list_of_datasets:
       name = ele.pop('dataset')
       tf = ele.pop('frac','-')
       dataset_cfacs = ele.pop('cfac','-')
       names.append(str(name))
       tfs.append(str(tf))
       cfacs.append(', '.join(dataset_cfacs))
       if ele:
          others.append(ele)
       else:
          others.append('-')
    df = pd.DataFrame({'Training fraction':tfs, 'C-factors':cfacs,
                       'Other fields':others}, index=names)
    df = df[['Training fraction', 'C-factors', 'Other fields']]
    df.index.name = 'Dataset'
    return df
