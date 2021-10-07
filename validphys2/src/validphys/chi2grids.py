"""
chi2grids.py

Compute and store χ² data from replicas, possibly keeping the correlations
between pseudorreplica fluctuations between different fits. This is applied
here to parameter determinations such as those of αs.
"""
import logging
from collections import namedtuple

import numpy as np
import pandas as pd

from reportengine import collect
from reportengine.table import table

from validphys.calcutils import calc_chi2
from validphys.n3fit_data import replica_mcseed
from validphys.pseudodata import make_replica

PseudoReplicaExpChi2Data = namedtuple(
    "PseudoReplicaChi2Data", ["group", "ndata", "chi2", "nnfit_index"]
)


log = logging.getLogger(__name__)


def computed_pseudoreplicas_chi2(
    mcseed,
    dataset_inputs_loaded_cd_with_cuts,
    fitted_replica_indexes,
    group_result_table_no_table,  # to get the results already in the form of a dataframe
    groups_sqrtcovmat,
):
    """Return a dataframe with the chi² of each replica with its corresponding
    pseudodata (i.e. the one it was fitted with). The chi² is computed by group.
    The index of the output dataframe is
        ``['group',  'ndata' , 'nnfit_index']``
    where ``nnftix_index`` is the name of the corresponding replica
    """
    # Get the replica pseudodata
    all_data_replicas = []
    for replica in fitted_replica_indexes:
        value_of_mcseed = replica_mcseed(replica, mcseed, True)
        all_data_replicas.append(make_replica(dataset_inputs_loaded_cd_with_cuts, value_of_mcseed))
    r_data = np.array(all_data_replicas).T
    ########################

    # Drop data central and theory central which is not useful here
    r_prediction = group_result_table_no_table.drop(columns=["data_central", "theory_central"])

    # Now compute the chi2 in a per-group basis
    diff = r_prediction - r_data
    group_level = r_prediction.index.get_level_values("group")
    groups = group_level.drop_duplicates().to_list()

    # Save the results in a dataframe similar (but not equal) to the old one
    df_output = []
    for group in groups:
        group_diff = diff.loc[group_level == group]
        its_covmat = groups_sqrtcovmat[group_level == group][group]
        chi2_per_replica = calc_chi2(its_covmat, group_diff)
        ndata = len(group_diff)
        for i, chi2 in enumerate(chi2_per_replica):
            df_output.append(PseudoReplicaExpChi2Data(group, ndata, chi2, i))

    df = pd.DataFrame(df_output, columns=PseudoReplicaExpChi2Data._fields)
    df.set_index(["group", "ndata", "nnfit_index"], inplace=True)
    df.sort_index(inplace=True)
    return df


# TODO: Probably fitcontext should set all of the variables required to compute
# this. But better setting
# them explicitly than setting some, so we require the user to do that.
fits_computed_pseudoreplicas_chi2 = collect(computed_pseudoreplicas_chi2, ("fits",))

dataspecs_computed_pseudorreplicas_chi2 = collect(computed_pseudoreplicas_chi2, ("dataspecs",))


@table
def export_fits_computed_pseudoreplicas_chi2(fits_computed_pseudoreplicas_chi2):
    """Hack to force writting the CSV output"""
    return fits_computed_pseudoreplicas_chi2
