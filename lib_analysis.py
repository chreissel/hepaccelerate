import os, glob
import argparse
import json
import numpy as np

import uproot
import hepaccelerate

from hepaccelerate.utils import Results, NanoAODDataset, Histogram, choose_backend

NUMPY_LIB = None
ha = None

############################################## OBJECT SELECTION ################################################

### Primary vertex selection
def vertex_selection(scalars, mask_events):

    PV_isfake = (scalars["PV_score"] == 0) & (scalars["PV_chi2"] == 0)
    PV_rho = NUMPY_LIB.sqrt(scalars["PV_x"]**2 + scalars["PV_y"]**2)
    mask_events = mask_events & (~PV_isfake) & (scalars["PV_ndof"] > 4) & (scalars["PV_z"]<24) & (PV_rho < 2)

    return mask_events


### Lepton selection
def lepton_selection(leps, cuts):

    passes_eta = (NUMPY_LIB.abs(leps.eta) < cuts["eta"])
    passes_subleading_pt = (leps.pt > cuts["subleading_pt"])
    passes_leading_pt = (leps.pt > cuts["leading_pt"])

    if cuts["type"] == "el":
        sca = NUMPY_LIB.abs(leps.deltaEtaSC + leps.eta)
        passes_id = (leps.cutBased >= 4)
        passes_SC = NUMPY_LIB.invert((sca >= 1.4442) & (sca <= 1.5660))
        # cuts taken from: https://twiki.cern.ch/twiki/bin/view/CMS/CutBasedElectronIdentificationRun2#Working_points_for_92X_and_later
        passes_impact = ((leps.dz < 0.10) & (sca <= 1.479)) | ((leps.dz < 0.20) & (sca > 1.479)) | ((leps.dxy < 0.05) & (sca <= 1.479)) | ((leps.dxy < 0.1) & (sca > 1.479))

        #select electrons
        good_leps = passes_eta & passes_leading_pt & passes_id & passes_SC & passes_impact
        veto_leps = passes_eta & passes_subleading_pt & NUMPY_LIB.invert(good_leps) & passes_id & passes_SC & passes_impact

    elif cuts["type"] == "mu":
        passes_leading_iso = (leps.pfRelIso04_all < cuts["leading_iso"])
        passes_subleading_iso = (leps.pfRelIso04_all < cuts["subleading_iso"])
        passes_id = (leps.tightId == 1)

        #select muons
        good_leps = passes_eta & passes_leading_pt & passes_leading_iso & passes_id
        veto_leps = passes_eta & passes_subleading_pt & passes_subleading_iso & passes_id & NUMPY_LIB.invert(good_leps)

    return good_leps, veto_leps

### Jet selection
def jet_selection(jets, leps, mask_leps, cuts, jets_met_corrected):

    jets_pass_dr = ha.mask_deltar_first(jets, jets.masks["all"], leps, mask_leps, cuts["dr"])
    jets.masks["pass_dr"] = jets_pass_dr
    if jets_met_corrected:
        good_jets = (jets.pt_nom > cuts["pt"]) & (NUMPY_LIB.abs(jets.eta) < cuts["eta"]) & (jets.jetId >= cuts["jetId"]) & jets_pass_dr
        if cuts["type"] == "jet":
            good_jets &= ((jets.puId>=cuts["puId"]) | (jets.pt_nom > 50.))   
            #good_jets &= (jets.puId>=cuts["puId"])   
    else:
        good_jets = (jets.pt > cuts["pt"]) & (NUMPY_LIB.abs(jets.eta) < cuts["eta"]) & (jets.jetId >= cuts["jetId"]) & jets_pass_dr
        if cuts["type"] == "jet":
            good_jets &= ((jets.puId>=cuts["puId"]) | (jets.pt > 50.)) 
            #good_jets &= (jets.puId>=cuts["puId"])  

    return good_jets


###################################################### WEIGHT / SF CALCULATION ##########################################################

### PileUp weight
def compute_pu_weights(pu_corrections_target, weights, mc_nvtx, reco_nvtx):

    pu_edges, (values_nom, values_up, values_down) = pu_corrections_target

    src_pu_hist = get_histogram(mc_nvtx, weights, pu_edges)
    norm = sum(src_pu_hist.contents)
    src_pu_hist.contents = src_pu_hist.contents/norm
    src_pu_hist.contents_w2 = src_pu_hist.contents_w2/norm

    ratio = values_nom / src_pu_hist.contents
    remove_inf_nan(ratio)
    pu_weights = NUMPY_LIB.zeros_like(weights)
    ha.get_bin_contents(reco_nvtx, NUMPY_LIB.array(pu_edges), NUMPY_LIB.array(ratio), pu_weights)
    #fix_large_weights(pu_weights)

    return pu_weights


def load_puhist_target(filename):
    fi = uproot.open(filename)

    h = fi["pileup"]
    edges = np.array(h.edges)
    values_nominal = np.array(h.values)
    values_nominal = values_nominal / np.sum(values_nominal)

    h = fi["pileup_plus"]
    values_up = np.array(h.values)
    values_up = values_up / np.sum(values_up)

    h = fi["pileup_minus"]
    values_down = np.array(h.values)
    values_down = values_down / np.sum(values_down)
    return edges, (values_nominal, values_up, values_down)


# lepton scale factors
def compute_lepton_weights(leps, lepton_x, lepton_y, mask_rows, mask_content, evaluator, SF_list):

    weights = NUMPY_LIB.ones(len(lepton_x))

    for SF in SF_list:

        if SF == "el_triggerSF":
            weights *= evaluator[SF](lepton_y, lepton_x)
        else:
            weights *= evaluator[SF](lepton_x, lepton_y)
        
    per_event_weights = ha.multiply_in_offsets(leps, weights, mask_rows, mask_content)
    return per_event_weights

# btagging scale factor 
def compute_btag_weights(jets, mask_rows, mask_content, sf, jets_met_corrected, btagalgorithm):

    pJet_weight = NUMPY_LIB.ones(len(mask_content))

    for tag in [0, 4, 5]:
        
        if jets_met_corrected:
            SF_btag = sf.eval('central', tag, abs(jets.eta), jets.pt_nom, getattr(jets, btagalgorithm), ignore_missing=True) 
        else:
            SF_btag = sf.eval('central', tag, abs(jets.eta), jets.pt, getattr(jets, btagalgorithm), ignore_missing=True) 
        if tag == 5:
            SF_btag[jets.hadronFlavour != 5] = 1.
        if tag == 4:
            SF_btag[jets.hadronFlavour != 4] = 1.
            SF_btag[jets.hadronFlavour == 4] = 1. #DIRTY FIX TO REMOVE WEIGHT CONTRIBUTIONS FROM C JETS! TO BE FIXED! ALSO WOULD BE WRONG FOR UNCERTAINTIES AS THEY ARE CALCULATED FOR C    
        if tag == 0:
            SF_btag[jets.hadronFlavour != 0] = 1.

        pJet_weight *= SF_btag

    per_event_weights = ha.multiply_in_offsets(jets, pJet_weight, mask_rows, mask_content)
    return per_event_weights

############################################# HIGH LEVEL VARIABLES (DNN evaluation, ...) ############################################

def evaluate_DNN(jets, good_jets, electrons, good_electrons, muons, good_muons, scalars, mask_events, nEvents, DNN, DNN_model, jets_met_corrected, outdir="./"):
    
        # make inputs (defined in backend (not extremely nice))
        if jets_met_corrected:
            jets_feats = ha.make_jets_inputs(jets, jets.offsets, 10, ["pt_nom","eta","phi","en","px","py","pz", "btagDeepFlavB"], mask_events, good_jets)
            met_feats = ha.make_met_inputs(scalars, nEvents, ["phi_nom","pt_nom","sumEt","px","py"], mask_events)
        else:
            jets_feats = ha.make_jets_inputs(jets, jets.offsets, 10, ["pt","eta","phi","en","px","py","pz", "btagDeepFlavB"], mask_events, good_jets)
            met_feats = ha.make_met_inputs(scalars, nEvents, ["phi","pt","sumEt","px","py"], mask_events)
        leps_feats = ha.make_leps_inputs(electrons, muons, nEvents, ["pt","eta","phi","en","px","py","pz"], mask_events, good_electrons, good_muons)
        
        if DNN == "save-arrays":
            NUMPY_LIB.save(outdir + "jets.npy", jets_feats[mask_events==1])
            NUMPY_LIB.save(outdir + "leps.npy", leps_feats[mask_events==1])
            NUMPY_LIB.save(outdir + "met.npy", met_feats[mask_events==1])
            
        
        inputs = [jets_feats, leps_feats, met_feats]

        if DNN.startswith("ffwd"):
            inputs = [NUMPY_LIB.reshape(x, (x.shape[0], -1)) for x in inputs]
            inputs = NUMPY_LIB.hstack(inputs)
            # numpy transfer needed for keras
            inputs = NUMPY_LIB.asnumpy(inputs)
            
        if DNN.startswith("cmb") or DNN.startswith("mass"):
            # numpy transfer needed for keras
            if "prtrn" in DNN:
                inputs = [inputs[0], inputs[1], inputs[2], inputs[0], inputs[1], inputs[2], inputs[0], inputs[1], inputs[2]]
            if not isinstance(jets_feats, np.ndarray):
                inputs = [NUMPY_LIB.asnumpy(x) for x in inputs]
                
        if DNN.startswith("gnet"):
            # implement function which converts jets leps and met into nodes, edges and mask
            if not isinstance(jets_feats, np.ndarray):
                inputs = [NUMPY_LIB.asnumpy(x) for x in inputs]
            edges, nodes, mask = make_graph_input(jets_feats, leps_feats, met_feats)
            inputs = [edges, nodes, mask]
            if not isinstance(edges, np.ndarray):
                inputs = [NUMPY_LIB.asnumpy(x) for x in inputs]
            if "fcn" in DNN:
                inputs=[nodes]

        # fix in case inputs are empty
        if jets_feats.shape[0] == 0:
            DNN_pred = NUMPY_LIB.zeros(nEvents, dtype=NUMPY_LIB.float32)
        else:
            # run prediction (done on GPU)
            #DNN_pred = DNN_model.predict(inputs, batch_size = 10000)
            # in case of NUMPY_LIB is cupy: transfer numpy output back to cupy array for further computation
            DNN_pred = NUMPY_LIB.array(DNN_model.predict(inputs, batch_size = 10000))
            if 'categorical' in DNN:
                DNN_pred = DNN_pred[:,1]
            #if DNN.endswith("binary"):
            #    DNN_pred = NUMPY_LIB.reshape(DNN_pred, DNN_pred.shape[0])

        print("DNN inference finished.")
        if DNN == "mass_fit":
            dijet_masses = ha.dijet_masses(jets_feats, mask_events, DNN_pred)

            return dijet_masses

        return DNN_pred

# calculate simple object variables
def calculate_variable_features(z, mask_events, indices, var):

    name, coll, mask_content, inds, feats = z
    idx = indices[inds]

    for f in feats:
        var[inds+"_"+name+"_"+f] = ha.get_in_offsets(getattr(coll, f), getattr(coll, "offsets"), idx, mask_events, mask_content)
    
####################################################### Simple helpers  #############################################################
def make_graph_input(jets_ft, leps_ft, met_ft):
    
    graph_jets = NUMPY_LIB.zeros((jets_ft.shape[0], jets_ft.shape[1], jets_ft.shape[2]+3))
    graph_jets[:, :, :8] = jets_ft
    graph_jets[:, :, 8] = 1
    
    graph_leps = NUMPY_LIB.zeros((leps_ft.shape[0], leps_ft.shape[1], leps_ft.shape[2]+4))
    graph_leps[:, :, :7] = leps_ft
    graph_leps[:, :, 9] = 1
    
    
    met_ft = NUMPY_LIB.expand_dims(met_ft, 1)
    # swap phi and pt for met
    pt_met = NUMPY_LIB.copy(met_ft[:, :, 1])
    pt_phi = NUMPY_LIB.copy(met_ft[:, :, 0])
    met_ft[:, :, 0] = pt_met
    met_ft[:, :, 1] = pt_phi
    
    graph_met = NUMPY_LIB.zeros((met_ft.shape[0], met_ft.shape[1], met_ft.shape[2]+6))
    graph_met[:, :, 0] = met_ft[:, :, 0]
    graph_met[:, :, 2:6] = met_ft[:, :, 1:]
    graph_met[:, :, 10] = 1
    
    full_nodes = NUMPY_LIB.concatenate((graph_jets, graph_leps, graph_met), axis=1)
    full_edges = NUMPY_LIB.copy(full_nodes[:, :, 1:3])
    full_mask = NUMPY_LIB.copy(full_nodes[:, :, 0])
    full_mask = NUMPY_LIB.expand_dims(full_mask, 2)
    
    return full_edges, full_nodes, full_mask


def get_histogram(data, weights, bins):
    return Histogram(*ha.histogram_from_vector(data, weights, bins))

def remove_inf_nan(arr):
    arr[np.isinf(arr)] = 0
    arr[np.isnan(arr)] = 0
    arr[arr < 0] = 0

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

import keras.backend as K
import keras.losses
import keras.utils.generic_utils
from Disco_tf import distance_corr

def mse0(y_true,y_pred):
    return K.mean( K.square(y_true[:,0] - y_pred[:,0]) )

def mae0(y_true,y_pred):
    return K.mean( K.abs(y_true[:,0] - y_pred[:,0]) )

def r2_score0(y_true,y_pred):
    return 1. - K.sum( K.square(y_true[:,0] - y_pred[:,0]) ) / K.sum( K.square(y_true[:,0] - K.mean(y_true[:,0]) ) )

def decorr(var_1, var_2, weights, kappa):

    def loss(y_true, y_pred):
        return keras.losses.categorical_crossentropy(y_true, y_pred) + kappa * distance_corr(var_1, var_2, weights)

    return loss

def dijet_feats(x):
# position depends on input array

    en = x[:,:,3] + x[:,:,11]
    px = x[:,:,4] + x[:,:,12]
    py = x[:,:,5] + x[:,:,13]
    pz = x[:,:,6] + x[:,:,14]

    m = K.sqrt(en*en - px*px - py*py - pz*pz)
    pt = K.sqrt(px*px + py*py)
    phi = tf.math.acos(py/px)
    theta = tf.math.acos(pz/(K.sqrt(px*px + py*py + pz*pz)))
    eta = -K.log(tf.math.tan(theta/2))

    pt = tf.reshape(pt, [-1,45,1])
    eta = tf.reshape(eta, [-1,45,1])
    phi = tf.reshape(phi, [-1,45,1])
    m = tf.reshape(m, [-1,45,1])
    return Concatenate(axis=2)([pt, eta, phi, m])

def trijet_feats(x):
# position depends on input array

    en = x[:,:,3] + x[:,:,11] + x[:,:,19]
    px = x[:,:,4] + x[:,:,12] + x[:,:,20]
    py = x[:,:,5] + x[:,:,13] + x[:,:,21]
    pz = x[:,:,6] + x[:,:,14] + x[:,:,22]

    m = K.sqrt(en*en - px*px - py*py - pz*pz)
    pt = K.sqrt(px*px + py*py)
    phi = tf.math.acos(py/px)
    theta = tf.math.acos(pz/(K.sqrt(px*px + py*py + pz*pz)))
    eta = -K.log(tf.math.tan(theta/2))

    pt = tf.reshape(pt, [-1,120,1])
    eta = tf.reshape(eta, [-1,120,1])
    phi = tf.reshape(phi, [-1,120,1])
    m = tf.reshape(m, [-1,120,1])
    return Concatenate(axis=2)([pt, eta, phi, m])

def lep_feats(x):
# position depends on input array

    px = x[:,:,4] + x[:,:,10] + x[:,:,16]
    py = x[:,:,5] + x[:,:,11] + x[:,:,17]

    pt = K.sqrt(px*px + py*py)
    phi = tf.math.acos(py/px)

    pt = tf.reshape(pt, [-1,10,1])
    phi = tf.reshape(phi, [-1,10,1])
    return Concatenate(axis=2)([pt, phi])


