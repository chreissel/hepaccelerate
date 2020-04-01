import os, glob
#os.environ["NUMBAPRO_NVVM"] = "/usr/local/cuda/nvvm/lib64/libnvvm.so"
#os.environ["NUMBAPRO_LIBDEVICE"] = "/usr/local/cuda/nvvm/libdevice/"
os.environ['KERAS_BACKEND'] = "tensorflow"
import argparse
import json
import numpy as np
import sys
from pprint import pprint

import uproot
import hepaccelerate
from hepaccelerate.utils import Results, NanoAODDataset, Histogram, choose_backend
import h5py

import tensorflow as tf
from tensorflow.keras.models import load_model, model_from_json
import itertools
from lib_analysis import mse0,mae0,r2_score0,decorr
from lib_analysis import trijet_feats, dijet_feats, lep_feats

from definitions_analysis import histogram_settings

import lib_analysis
from lib_analysis import vertex_selection, lepton_selection, jet_selection, load_puhist_target, compute_pu_weights, compute_lepton_weights, compute_btag_weights, chunks, evaluate_DNN, calculate_variable_features

# For TensorFlow 1.x
if tf.__version__.startswith('1'):
    config = tf.ConfigProto()
    config.gpu_options.allow_growth=True
    sess = tf.Session(config=config)
# For TensorFlow 2.x
if tf.__version__.startswith('2'):
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
      try:
        # Currently, memory growth needs to be the same across GPUs
        for gpu in gpus:
          tf.config.experimental.set_memory_growth(gpu, True)
      except RuntimeError as e:
        # Memory growth must be set before GPUs have been initialized
        print(e)

def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size

#This function will be called for every file in the dataset
def analyze_data(data, sample, NUMPY_LIB=None, parameters={}, samples_info={}, is_mc=True, lumimask=None, cat=False, DNN=False, DNN_model=None, jets_met_corrected=True, outdir="./", btag_DNN='deepCSV'):
    #Output structure that will be returned and added up among the files.
    #Should be relatively small.
    ret = Results()

    muons = data["Muon"]
    electrons = data["Electron"]
    scalars = data["eventvars"]
    jets = data["Jet"]
    
    muons.energy = ha.calc_en(muons.pt, muons.eta, muons.mass)
    electrons.energy = ha.calc_en(electrons.pt, electrons.eta, electrons.mass)
    jets.energy = ha.calc_en(jets.pt, jets.eta, jets.mass)
    muons.px = ha.calc_px(muons.pt, muons.phi)
    electrons.px = ha.calc_px(electrons.pt, electrons.phi)
    jets.px = ha.calc_px(jets.pt, jets.phi)
    muons.py = ha.calc_py(muons.pt, muons.phi)
    electrons.py = ha.calc_py(electrons.pt, electrons.phi)
    jets.py = ha.calc_py(jets.pt, jets.phi)
    muons.pz = ha.calc_pz(muons.pt, muons.eta)
    electrons.pz = ha.calc_pz(electrons.pt, electrons.eta)
    jets.pz = ha.calc_pz(jets.pt, jets.eta)

    nEvents = muons.numevents()
    indices = {}
    indices["leading"] = NUMPY_LIB.zeros(nEvents, dtype=NUMPY_LIB.int32)
    indices["subleading"] = NUMPY_LIB.ones(nEvents, dtype=NUMPY_LIB.int32)
    indices["third"] = NUMPY_LIB.full(nEvents, 2, dtype=NUMPY_LIB.int32)
    indices["fourth"] = NUMPY_LIB.full(nEvents, 3, dtype=NUMPY_LIB.int32)
    indices["fifth"] = NUMPY_LIB.full(nEvents, 4, dtype=NUMPY_LIB.int32)
    indices["sixth"] = NUMPY_LIB.full(nEvents, 5, dtype=NUMPY_LIB.int32)
    indices["seventh"] = NUMPY_LIB.full(nEvents, 6, dtype=NUMPY_LIB.int32)
    indices["eighth"] = NUMPY_LIB.full(nEvents, 7, dtype=NUMPY_LIB.int32)
    indices["ninth"] = NUMPY_LIB.full(nEvents, 8, dtype=NUMPY_LIB.int32)
    indices["tenth"] = NUMPY_LIB.full(nEvents, 9, dtype=NUMPY_LIB.int32)

    mask_events = NUMPY_LIB.ones(nEvents, dtype=NUMPY_LIB.bool)

    # apply event cleaning and PV selection
    flags = [
        "Flag_goodVertices", "Flag_globalSuperTightHalo2016Filter", "Flag_HBHENoiseFilter", "Flag_HBHENoiseIsoFilter", "Flag_EcalDeadCellTriggerPrimitiveFilter", "Flag_BadPFMuonFilter", "Flag_BadChargedCandidateFilter", "Flag_ecalBadCalibFilter"]
    if not is_mc:
        flags.append("Flag_eeBadScFilter")
    for flag in flags:
        mask_events = mask_events & scalars[flag]
    mask_events = mask_events & (scalars["PV_npvsGood"]>0)
    #mask_events = vertex_selection(scalars, mask_events)

    # apply object selection for muons, electrons, jets
    good_muons, veto_muons = lepton_selection(muons, parameters["muons"])
    good_electrons, veto_electrons = lepton_selection(electrons, parameters["electrons"])
    good_jets = jet_selection(jets, muons, (veto_muons | good_muons), parameters["jets"], jets_met_corrected) & jet_selection(jets, electrons, (veto_electrons | good_electrons) , parameters["jets"], jets_met_corrected)
    bjets = good_jets & (getattr(jets, parameters["btagging algorithm"]) > parameters["btagging WP"][parameters["btagging algorithm"]])

    # apply basic event selection -> individual categories cut later
    nleps =  NUMPY_LIB.add(ha.sum_in_offsets(muons, good_muons, mask_events, muons.masks["all"], NUMPY_LIB.int8), ha.sum_in_offsets(electrons, good_electrons, mask_events, electrons.masks["all"], NUMPY_LIB.int8))
    nMuons =  ha.sum_in_offsets(muons, good_muons, mask_events, muons.masks["all"], NUMPY_LIB.int8)
    nElectrons = ha.sum_in_offsets(electrons, good_electrons, mask_events, electrons.masks["all"], NUMPY_LIB.int8)
    
    lepton_veto = NUMPY_LIB.add(ha.sum_in_offsets(muons, veto_muons, mask_events, muons.masks["all"], NUMPY_LIB.int8), ha.sum_in_offsets(electrons, veto_electrons, mask_events, electrons.masks["all"], NUMPY_LIB.int8))
    njets = ha.sum_in_offsets(jets, good_jets, mask_events, jets.masks["all"], NUMPY_LIB.int8)

    btags = ha.sum_in_offsets(jets, bjets, mask_events, jets.masks["all"], NUMPY_LIB.int8)
    if jets_met_corrected:
        #met = (scalars["MET_pt_nom"] > 20)
        met = (scalars["METFixEE2017_pt_nom"] > 20)
    else: 
        met = (scalars["MET_pt"] > 20)

    # trigger logic
    # needs update for different years!
    trigger_el = (scalars["HLT_Ele35_WPTight_Gsf"] | scalars["HLT_Ele28_eta2p1_WPTight_Gsf_HT150"] ) & (nleps == 1) & (nElectrons == 1)
    trigger_mu = (scalars["HLT_IsoMu27"] ) & (nleps == 1) & (nMuons == 1)
    if not is_mc:
        if "SingleMuon" in sample:
            trigger_el = NUMPY_LIB.zeros(nEvents, dtype=NUMPY_LIB.bool)
        if "SingleElectron" in sample:
            trigger_mu = NUMPY_LIB.zeros(nEvents, dtype=NUMPY_LIB.bool)
    mask_events = mask_events & (trigger_el | trigger_mu)

    mask_events = mask_events & (nleps == 1) & (lepton_veto == 0) & (njets >= 4) & (btags >=2) & met

    ### calculation of all needed variables
    var = {}

    var["njets"] = njets
    var["btags"] = btags
    var["nleps"] = nleps

    if jets_met_corrected: pt_label = "pt_nom"
    else: pt_label = "pt"
    variables = [
        ("jet", jets, good_jets, "leading", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "subleading", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "third", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "fourth", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "fifth", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "sixth", [pt_label, "eta", "phi", "btagDeepFlavB",  "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "seventh", [pt_label, "eta", "phi", "btagDeepFlavB",  "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "eighth", [pt_label, "eta", "phi", "btagDeepFlavB", "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "ninth", [pt_label, "eta", "phi", "btagDeepFlavB",  "energy", "px", "py", "pz"]),
        ("jet", jets, good_jets, "tenth", [pt_label, "eta", "phi", "btagDeepFlavB",  "energy", "px", "py", "pz"]),
        ("bjet", jets, bjets, "leading", [pt_label, "eta"]),
    ]

    # special role of lepton
    var["leading_lepton_pt"] = NUMPY_LIB.maximum(ha.get_in_offsets(muons.pt, muons.offsets, indices["leading"], mask_events, good_muons), ha.get_in_offsets(electrons.pt, electrons.offsets, indices["leading"], mask_events, good_electrons))
    compare_leps = ha.get_in_offsets(muons.pt, muons.offsets, indices["leading"], mask_events, good_muons) >= ha.get_in_offsets(electrons.pt, electrons.offsets, indices["leading"], mask_events, good_electrons)
    
    leading_lepton_eta = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_eta[compare_leps] = ha.get_in_offsets(muons.eta, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_eta[~compare_leps] = ha.get_in_offsets(electrons.eta, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_eta"] = leading_lepton_eta
    
    leading_lepton_phi = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_phi[compare_leps] = ha.get_in_offsets(muons.phi, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_phi[~compare_leps] = ha.get_in_offsets(electrons.phi, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_phi"] = leading_lepton_phi

    leading_lepton_energy = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_energy[compare_leps] = ha.get_in_offsets(muons.energy, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_energy[~compare_leps] = ha.get_in_offsets(electrons.energy, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_energy"] = leading_lepton_energy

    leading_lepton_px = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_px[compare_leps] = ha.get_in_offsets(muons.px, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_px[~compare_leps] = ha.get_in_offsets(electrons.px, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_px"] = leading_lepton_px
    
    leading_lepton_py = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_py[compare_leps] = ha.get_in_offsets(muons.py, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_py[~compare_leps] = ha.get_in_offsets(electrons.py, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_py"] = leading_lepton_py
    
    leading_lepton_pz = NUMPY_LIB.zeros(compare_leps.shape[0])
    leading_lepton_pz[compare_leps] = ha.get_in_offsets(muons.pz, muons.offsets, indices["leading"], mask_events, good_muons)[compare_leps]
    leading_lepton_pz[~compare_leps] = ha.get_in_offsets(electrons.pz, electrons.offsets, indices["leading"], mask_events, good_electrons)[~compare_leps]
    var["leading_lepton_pz"] = leading_lepton_pz
    
    var["MET_pt"] = scalars["MET_pt"]
    var["MET_phi"] = scalars["MET_phi"]
    var["MET_sumEt"] = scalars["MET_sumEt"]
    var["MET_px"] = ha.calc_px(scalars["MET_pt"], scalars["MET_phi"])
    var["MET_py"] = ha.calc_py(scalars["MET_pt"], scalars["MET_phi"])

    # all other variables
    for v in variables:
        calculate_variable_features(v, mask_events, indices, var)

    #synch
    #mask = (scalars["event"] == 2895765)

    # calculate weights for MC samples
    weights = {}
    weights["nominal"] = NUMPY_LIB.ones(nEvents, dtype=NUMPY_LIB.float32)

    if is_mc:
        weights["nominal"] = weights["nominal"] * scalars["genWeight"] * parameters["lumi"] * samples_info[sample]["XS"] / samples_info[sample]["ngen_weight"]

        # pu corrections
        #pu_weights = compute_pu_weights(parameters["pu_corrections_target"], weights["nominal"], scalars["Pileup_nTrueInt"], scalars["PV_npvsGood"])
        pu_weights = compute_pu_weights(parameters["pu_corrections_target"], weights["nominal"], scalars["Pileup_nTrueInt"], scalars["Pileup_nTrueInt"])
        weights["nominal"] = weights["nominal"] * pu_weights
        var["pu_weights"] = pu_weights

        # lepton SF corrections
        electron_weights = compute_lepton_weights(electrons, (electrons.deltaEtaSC + electrons.eta), electrons.pt, mask_events, good_electrons, evaluator, ["el_triggerSF", "el_recoSF", "el_idSF"])
        muon_weights = compute_lepton_weights(muons, muons.pt, NUMPY_LIB.abs(muons.eta), mask_events, good_muons, evaluator, ["mu_triggerSF", "mu_isoSF", "mu_idSF"])
        weights["nominal"] = weights["nominal"] * muon_weights * electron_weights

        # btag SF corrections
        #if btag_sf_var == 'up':
        #    sys_str = [
        #    'up_'
        #    ]
        #elif btag_sf_var == 'down':
        #    
        #else:
        btag_weights = compute_btag_weights(jets, mask_events, good_jets, parameters["btag_SF_target"], jets_met_corrected, parameters["btagging algorithm"])
        var["btag_weights"] = btag_weights
        weights["nominal"] = weights["nominal"] * btag_weights
        if DNN == "save-arrays":
            scalars["njets"] = njets
            scalars["n"+btag_DNN] = btags
            scalars["nleps"] = nleps
            mask_scalars = Results()
            for key in scalars:
                mask_scalars[key+'_arrays'] = scalars[key][mask_events==1]
            
            ret['weights_arrays'] = weights["nominal"][mask_events==1]
            ret['evdesc'] = mask_scalars

    #in case of data: check if event is in golden lumi file
    if not is_mc and not (lumimask is None):
        mask_lumi = lumimask(scalars["run"], scalars["luminosityBlock"])
        mask_events = mask_events & mask_lumi

    #evaluate DNN
    if DNN:
        DNN_pred = evaluate_DNN(jets, good_jets, electrons, good_electrons, muons, good_muons, scalars, mask_events, nEvents, DNN, DNN_model, jets_met_corrected, outdir, btag_DNN)
        if DNN == 'save-arrays':
            ret['jets_arrays'], ret['leps_arrays'], ret['met_arrays'] = DNN_pred

    # in case of tt+jets -> split in ttbb, tt2b, ttb, ttcc, ttlf
    processes = {}
    if sample.startswith("TT"):
        ttCls = scalars["genTtbarId"]%100
        processes["ttbb"] = mask_events & (ttCls >=53) & (ttCls <=56)
        processes["tt2b"] = mask_events & (ttCls ==52)
        processes["ttb"] = mask_events & (ttCls ==51)
        processes["ttcc"] = mask_events & (ttCls >=41) & (ttCls <=45)
        ttHF =  ((ttCls >=53) & (ttCls <=56)) | (ttCls ==52) | (ttCls ==51) | ((ttCls >=41) & (ttCls <=45))
        processes["ttlf"] = mask_events & NUMPY_LIB.invert(ttHF)
        
        # in case of multiclassifier, make target and save it!
        if DNN=="save-arrays":
            target = NUMPY_LIB.zeros((mask_events[mask_events==1].shape[0],5))
            target[:, 0] = processes["ttbb"][mask_events==1]
            target[:, 1] = processes["tt2b"][mask_events==1]
            target[:, 2] = processes["ttb"][mask_events==1]
            target[:, 3] = processes["ttcc"][mask_events==1]
            target[:, 4] = processes["ttlf"][mask_events==1]
            ret['multi_tgt_arrays'] = target
    else:
        processes["unsplit"] = mask_events

    for p in processes.keys():

        mask_events_split = processes[p]

        # Categories
        categories = {}
        categories["sl_jge4_tge2"] = mask_events_split
        categories["sl_jge4_tge3"] = mask_events_split & (btags >=3)
        categories["sl_jge4_tge4"] = mask_events_split & (btags >=4)

        categories["sl_j4_tge3"] = mask_events_split & (njets ==4) & (btags >=3)
        categories["sl_j5_tge3"] = mask_events_split & (njets ==5) & (btags >=3)
        categories["sl_jge6_tge3"] = mask_events_split & (njets >=6) & (btags >=3)

        categories["sl_j4_t3"] = mask_events_split & (njets ==4) & (btags ==3)
        categories["sl_j4_tge4"] = mask_events_split & (njets ==4) & (btags >=4)
        categories["sl_j5_t3"] = mask_events_split & (njets ==5) & (btags ==3)
        categories["sl_j5_tge4"] = mask_events_split & (njets ==5) & (btags >=4)
        categories["sl_jge6_t3"] = mask_events_split & (njets >=6) & (btags ==3)
        categories["sl_jge6_tge4"] = mask_events_split & (njets >=6) & (btags >=4)

        #print("sl_j4_t3", scalars["event"][categories["sl_j4_t3"]], len(scalars["event"][categories["sl_j4_t3"]]))       
        #print("sl_j5_t3", scalars["event"][categories["sl_j5_t3"]], len(scalars["event"][categories["sl_j5_t3"]]))       
        #print("sl_jge6_t3", scalars["event"][categories["sl_jge6_t3"]], len(scalars["event"][categories["sl_jge6_t3"]]))       
        #print("sl_j4_tge4", scalars["event"][categories["sl_j4_tge4"]], len(scalars["event"][categories["sl_j4_tge4"]]))       
        #print("sl_j5_tge4", scalars["event"][categories["sl_j5_tge4"]], len(scalars["event"][categories["sl_j5_tge4"]]))       
        #print("sl_jge6_tge4", scalars["event"][categories["sl_jge6_tge4"]], len(scalars["event"][categories["sl_jge6_tge4"]]))       

        if not isinstance(cat, list):
            cat = [cat] 
        for c in cat:
            cut = categories[c]
            cut_name = c

            if p=="unsplit":
                if "Run" in sample:
                    name = "data" + "_" + cut_name
                else:
                    name = samples_info[sample]["process"] + "_" + cut_name
            else:
                name = p + "_" + cut_name

            # create histograms filled with weighted events
            for k in var.keys():
                if not k in histogram_settings.keys():
                    raise Exception("please add variable {0} to definitions_analysis.py".format(k))
                hist = Histogram(*ha.histogram_from_vector(var[k][cut], weights["nominal"][cut], NUMPY_LIB.linspace(histogram_settings[k][0], histogram_settings[k][1], histogram_settings[k][2])))
                ret["hist_{0}_{1}".format(name, k)] = hist

            if DNN and DNN != "save-arrays":
                if DNN.endswith("multiclass"):
                    # TODO: Find out if class weights should be multiplied here as well
                    class_pred = NUMPY_LIB.argmax(DNN_pred, axis=1)
                    for n, n_name in zip([0,1,2,3,4,5], ["ttH", "ttbb", "tt2b", "ttb", "ttcc", "ttlf"]):
                        node = (class_pred == n) #remove this and instead of (cut & node) just put cut
                        DNN_node = DNN_pred[:,n]
                        hist_DNN = Histogram(*ha.histogram_from_vector(DNN_node[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,1.,16)))
                        ret["hist_{0}_DNN_{1}".format(name, n_name)] = hist_DNN
                        hist_DNN_pred = Histogram(*ha.histogram_from_vector(DNN_node[(cut & node)], weights["nominal"][(cut & node)], NUMPY_LIB.linspace(0.,1.,16)))
                        ret["hist_{0}_DNN_pred_{1}".format(name, n_name)] = hist_DNN_pred
                        hist_DNN_ROC = Histogram(*ha.histogram_from_vector(DNN_node[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,1.,1000)))
                        ret["hist_{0}_DNN_ROC_{1}".format(name, n_name)] = hist_DNN_ROC
                        #hist_DNN_zoom = Histogram(*ha.histogram_from_vector(DNN_pred[(cut & node)], weights["nominal"][(cut & node)], NUMPY_LIB.linspace(0.,170.,30)))
                        #ret["hist_{0}_DNN_zoom_{1}".format(name, n_name)] = hist_DNN_zoom
                elif DNN=="mass_fit":
                    hist_DNN = Histogram(*ha.histogram_from_vector(DNN_pred[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,300.,30)))
                    hist_DNN_zoom = Histogram(*ha.histogram_from_vector(DNN_pred[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,170.,30)))
                    ret["hist_{0}_DNN".format(name)] = hist_DNN
                    ret["hist_{0}_DNN_zoom".format(name)] = hist_DNN_zoom
                else:
                    hist_DNN = Histogram(*ha.histogram_from_vector(DNN_pred[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,1.,16)))
                    hist_DNN_zoom = Histogram(*ha.histogram_from_vector(DNN_pred[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,170.,30)))
                    hist_DNN_ROC = Histogram(*ha.histogram_from_vector(DNN_pred[cut], weights["nominal"][cut], NUMPY_LIB.linspace(0.,1.,1000)))
                    ret["hist_{0}_DNN_ROC".format(name)] = hist_DNN_ROC
                    ret["hist_{0}_DNN".format(name)] = hist_DNN
                    ret["hist_{0}_DNN_zoom".format(name)] = hist_DNN_zoom


    #TODO: implement JECs

    ## To display properties of a single event
    #evts = [5991859]
    #mask = NUMPY_LIB.zeros_like(mask_events)
    #for iev in evts:
    #  mask |= (scalars["event"] == iev)
    ##import pdb
    ##pdb.set_trace()
    #print("mask", mask)
    #print('nevt', scalars["event"][mask])
    #print('pass sel', mask_events[mask])
    #print('nleps', nleps[mask])
    #print('njets', njets[mask])
    ##print('met', scalars['MET_pt_nom'][mask])
    ##print('lep_pt', leading_lepton_pt[mask])
    ##print('jet_pt', leading_jet_pt[mask])
    ##print('lep_eta', leading_lepton_eta[mask])
    #print('pu_weight', pu_weights[mask])
    #print('btag_weight', btag_weights[mask])
    #print('lep_weight', muon_weights[mask] * electron_weights[mask])
    #print('nevents', np.count_nonzero(mask_events))

    #np.set_printoptions(formatter={'float': lambda x: "{0:0.3f}".format(x)})
    #for evt in evts:
    #    evt_idx = NUMPY_LIB.where( scalars["event"] == evt )[0][0]
    #    start = jets.offsets[evt_idx]
    #    stop  = jets.offsets[evt_idx+1]
    #    print(f'!!! EVENT {evt} !!!')
    #    print(f'njets good {njets[evt_idx]}, total {stop-start}')
    #    #print('jets mask', nonbjets[start:stop])
    #    print('jets pt', jets.pt_nom[start:stop])
    #    print('jets eta', jets.eta[start:stop])
    #    print('jets btag', getattr(jets, parameters["btagging algorithm"])[start:stop])
    #    print('jet Id', jets.jetId[start:stop]),
    #    print('jet puId', jets.puId[start:stop])

    return ret

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Runs a simple array-based analysis')
    parser.add_argument('--use-cuda', action='store_true', help='Use the CUDA backend')
    parser.add_argument('--from-cache', action='store_true', help='Load from cache (otherwise create it)')
    parser.add_argument('--nthreads', action='store', help='Number of CPU threads to use', type=int, default=1, required=False)
    parser.add_argument('--files-per-batch', action='store', help='Number of files to process per batch', type=int, default=1, required=False)
    parser.add_argument('--cache-location', action='store', help='Path prefix for the cache, must be writable', type=str, default=os.path.join(os.getcwd(), 'cache'))
    parser.add_argument('--cache-only', action='store_true', help='Produce only cached files')
    parser.add_argument('--jets-met-corrected', action='store_true', help='defines usage of pt_nom vs pt for jets and MET', default=False)
    parser.add_argument('--outdir', action='store', help='directory to store outputs', type=str, default=os.getcwd())
    parser.add_argument('--outtag', action='store', help='outtag added to output file', type=str, default="")
    parser.add_argument('--filelist', action='store', help='List of files to load', type=str, default=None, required=False)
    parser.add_argument('--sample', action='store', help='sample name', type=str, default=None, required=True)
    parser.add_argument('--DNN', action='store', choices=['gnet_categorical_binary', 'gnet_fcn_categorical_binary', 'gnet_multiclass', 'gnet_fcn_multiclass','save-arrays','cmb_binary', 'cmb_multiclass', 'ffwd_binary', 'ffwd_multiclass', 'ffwd_categorical_binary', 'cmb_categorical_binary','cmb_categorical_prtrn_binary',False, 'mass_fit'], help='options for DNN evaluation / preparation', default=False)
    parser.add_argument('--btag-DNN', action='store', choices=['deepCSV', 'CSVV2','deepFlav'], help='choose which btagger to use for DNN evaluation or saving arrays', default='deepCSV')
    parser.add_argument('--categories', nargs='+', help='categories to be processed (default: sl_jge4_tge2)', default="sl_jge4_tge2")
    parser.add_argument('--path-to-model', action='store', help='path to DNN model', type=str, default=None, required=False)
    parser.add_argument('--year', action='store', choices=['2016', '2017', '2018'], help='Year of data/MC samples', default='2017')
    parser.add_argument('filenames', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    
    # set CPU or GPU backend
    NUMPY_LIB, ha = choose_backend(args.use_cuda)
    lib_analysis.NUMPY_LIB, lib_analysis.ha = NUMPY_LIB, ha
    NanoAODDataset.numpy_lib = NUMPY_LIB

    if args.use_cuda:
        os.environ["HEPACCELERATE_CUDA"] = "1"
    else:
        os.environ["HEPACCELERATE_CUDA"] = "0"

    from coffea.util import USE_CUPY
    from coffea.lumi_tools import LumiMask, LumiData
    from coffea.lookup_tools import extractor
    from coffea.btag_tools import BTagScaleFactor

    # load definitions
    from definitions_analysis import parameters, eraDependentParameters, samples_info
    parameters.update(eraDependentParameters[args.year])
    print(parameters)
    
    outdir = args.outdir
    if not os.path.exists(outdir):
        print(os.getcwd())
        os.makedirs(outdir)

    if "Run" in args.sample:
        is_mc = False
        lumimask = LumiMask(parameters["lumimask"])
    else:
        is_mc = True
        lumimask = None


    #define arrays to load: these are objects that will be kept together
    arrays_objects = [
        "Jet_eta", "Jet_phi", "Jet_btagDeepB", "Jet_btagCSVV2", "Jet_jetId", "Jet_puId", "Jet_btagDeepFlavB", #add for DeepFlavour
        "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_pfRelIso04_all", "Muon_tightId", "Muon_charge", "Muon_pdgId",
        "Electron_pt", "Electron_eta", "Electron_phi", "Electron_mass", "Electron_charge", "Electron_deltaEtaSC", "Electron_cutBased", "Electron_dz", "Electron_dxy", "Electron_pdgId",
    ]
    #these are variables per event
    arrays_event = [
        "PV_npvsGood", "PV_ndof", "PV_npvs", "PV_score", "PV_x", "PV_y", "PV_z", "PV_chi2",
        "Flag_goodVertices", "Flag_globalSuperTightHalo2016Filter", "Flag_HBHENoiseFilter", "Flag_HBHENoiseIsoFilter", "Flag_EcalDeadCellTriggerPrimitiveFilter", "Flag_BadPFMuonFilter", "Flag_BadChargedCandidateFilter", "Flag_eeBadScFilter", "Flag_ecalBadCalibFilter",
        "MET_sumEt",
        "run", "luminosityBlock", "event",
    ]

    if args.year.startswith('2016'): arrays_event += [ "HLT_Ele27_WPTight_Gsf", "HLT_IsoMu24", "HLT_IsoTkMu24" ]
    else: arrays_event += [ "HLT_Ele35_WPTight_Gsf", "HLT_Ele28_eta2p1_WPTight_Gsf_HT150", "HLT_IsoMu27" ]

    if args.sample.startswith("TT"): arrays_event.append("genTtbarId")

    if args.jets_met_corrected:
        #arrays_event += ["MET_pt_nom", "MET_phi_nom"]
        arrays_event += ["METFixEE2017_pt_nom", "METFixEE2017_phi_nom"]
        arrays_objects += ["Jet_pt_nom", "Jet_mass_nom"]
    else:
        arrays_event += ["MET_pt", "MET_phi"]
        arrays_objects += ["Jet_pt", "Jet_mass"]

    if is_mc: 
        arrays_objects += ["Jet_hadronFlavour"] 
        arrays_event += ["PV_npvsGood", "Pileup_nTrueInt", "genWeight", "nGenPart"]
        #arrays_event += ["MET_pt_nom", "MET_phi_nom"]

    filenames = None
    if not args.filelist is None:
        filenames = [l.strip() for l in open(args.filelist).readlines()]
    else:
        filenames = args.filenames

    print("Number of files:", len(filenames))

    for fn in filenames:
        if not fn.endswith(".root"):
            print(fn)
            raise Exception("Must supply ROOT filename, but got {0}".format(fn))
    
    # in case of DNN evaluation: load model
    model = None
    if args.DNN and args.DNN != 'save-arrays' and not args.cache_only:
        f = h5py.File(args.path_to_model, 'r')
        model = load_model(f)#, custom_objects=dict(itertools=itertools, mse0=mse0, mae0=mae0, r2_score0=r2_score0))
        f.close()
        #json_file = open(args.path_to_model + "model.json", "r")
        #loaded_model_json = json_file.read()
        #json_file.close()
        #model = model_from_json(loaded_model_json, custom_objects=dict(itertools=itertools))
        #model.load_weights(args.path_to_model + "model.hdf5")

    
    
    results = Results()


    for ibatch, files_in_batch in enumerate(chunks(filenames, args.files_per_batch)):
        #define our dataset
        print("Current file: {}".format(files_in_batch))
        structs = ["Jet", "Muon", "Electron"]
        #dataset = NanoAODDataset(files_in_batch, arrays_objects + arrays_event, "Events", structs, arrays_event)
        dataset = NanoAODDataset(files_in_batch, arrays_objects + arrays_event, "Events", structs, arrays_event)
        dataset.get_cache_dir = lambda fn,loc=args.cache_location: os.path.join(loc, fn)

        if not args.from_cache:
            #Load data from ROOT files
            dataset.preload(nthreads=args.nthreads, verbose=True)

            #prepare the object arrays on the host or device
            dataset.make_objects()

            print("preparing dataset cache")
            #save arrays for future use in cache
            dataset.to_cache(verbose=True, nthreads=args.nthreads)


        #Optionally, load the dataset from an uncompressed format
        else:
            print(files_in_batch)
            print("loading dataset from cache")
            dataset.from_cache(verbose=True, nthreads=args.nthreads)

        if not args.cache_only:

            if is_mc:

                # add information needed for MC corrections
                parameters["pu_corrections_target"] = load_puhist_target(parameters["pu_corrections_file"])
                parameters["btag_SF_target"] = BTagScaleFactor(parameters["btag_SF_{}".format(parameters["btagging algorithm"])], BTagScaleFactor.RESHAPE, 'iterativefit,iterativefit,iterativefit', keep_df=True) 

                ext = extractor()
                for corr in parameters["corrections"]:
                    ext.add_weight_sets([corr])
                ext.finalize()
                evaluator = ext.make_evaluator()

            if ibatch == 0:
                print(dataset.printout())

            print(args.categories)

            #### this is where the magic happens: run the main analysis
            results += dataset.analyze(analyze_data, NUMPY_LIB=NUMPY_LIB, parameters=parameters, is_mc = is_mc, lumimask=lumimask, cat=args.categories, sample=args.sample, samples_info=samples_info, DNN=args.DNN, DNN_model=model, jets_met_corrected=args.jets_met_corrected, outdir=args.outdir, btag_DNN = args.btag_DNN)
            
    if args.DNN == 'save-arrays':
        print("results keys: {}".format(results.keys()))
        NUMPY_LIB.save(outdir + 'jets.npy', results.pop('jets_arrays'))
        NUMPY_LIB.save(outdir + 'leps.npy', results.pop('leps_arrays'))
        NUMPY_LIB.save(outdir + 'met.npy', results.pop('met_arrays'))
        if args.sample.startswith("TT"):
            NUMPY_LIB.save(outdir + 'multiclass_tgt.npy', results.pop('multi_tgt_arrays'))
        NUMPY_LIB.save(outdir + 'weights.npy', results.pop('weights_arrays'))
        # remove '_arrays' from keys of evdesc
        evdesc = results.pop('evdesc')
        keylist = list(evdesc.keys())
        for i in range(len(keylist)):
            keylist[i] = keylist[i][:-7]
        evdesc = dict(zip(keylist, list(evdesc.values())))
        # save dict with scalars as pickle file
        import pickle
        with open(outdir + 'evdesc.pkl', 'wb') as pickle_file:
            pickle.dump(evdesc, pickle_file)
        
    print(results)
    #Save the results
    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    results.save_json(os.path.join(outdir,"out_{0}{1}.json".format(args.sample, args.outtag)))
