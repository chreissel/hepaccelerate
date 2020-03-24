

######################################## Selection criteria / Inputs for corrections ############################################

parameters = {
    "muons": {
                "type": "mu",
                "leading_pt": 29,
                "subleading_pt": 15,
                "eta": 2.4,
                "leading_iso": 0.15,
                "subleading_iso": 0.25,
                },

    "electrons" : {
                    "type": "el",
                    "leading_pt": 30,
                    "subleading_pt": 15,
                    "eta": 2.4
                    },
    "jets": {
            "type": "jet",
            "dr": 0.4,
            "pt": 30,
            "eta": 2.4,
            #"jetId": 2,
            "jetId": 4,
            "puId": 4
    },
    "fatjets": {
               "type": "fatjet",
               "dr": 0.8,
               "pt": 200,
               "eta": 2.4,
               "jetId": 2,
               "tau32cut": 0.4,
               "tau21cut": 0.4,
    },
}

eraDependentParameters = {
    "2016" : {
        "lumi":  35922.0,
        "lumimask": "data/Cert_271036-284044_13TeV_23Sep2016ReReco_Collisions16_JSON.txt",
        "pu_corrections_file" : "data/puData2017_withVar.root",
        "corrections" : [
            "el_triggerSF Ele27_WPTight_Gsf data/TriggerSF_Run2016All_v1.root",
            "el_recoSF EGamma_SF2D data/egammaEffi.txt_EGM2D.root",
            "el_idSF EGamma_SF2D data/egammaEffi.txt_EGM2D.root",
            "mu_triggerSF IsoMu27_PtEtaBins/pt_abseta_ratio data/EfficienciesAndSF_RunBtoF_Nov17Nov2017.histo.root",
            "mu_isoSF NUM_TightRelIso_DEN_TightIDandIPCut_pt_abseta data/RunBCDEF_SF_ISO.histo.root",
            "mu_idSF NUM_TightID_DEN_genTracks_pt_abseta data/RunBCDEF_SF_ID.histo.root",
            "BTagSF * data/DeepCSV_Moriond17_B_H.csv"
        ]
    },
    "2017" : {
        "lumi":  41529.0,
        "lumimask": "data/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON.txt",
        "pu_corrections_file" : "data/pileup_Cert_294927-306462_13TeV_PromptReco_Collisions17_withVar.root",
        "btag_SF_btagDeepB" : "./data/DeepCSV_94XSF_V5_B_F.btag.csv",
        "btag_SF_btagCSVV2" : "./data/CSVv2_94XSF_V2_B_F_2017.btag.csv",
        "btag_SF_btagDeepFlavB" : "./data/sfs_deepjet_2017_19-11-11.btag.csv",
        #"BTagSFbtagCSVV2 * ./data/CSVv2_94XSF_V2_B_F_2017.btag.csv",
        #"btag_SF_btagDeepB * ./data/deepCSV_sfs_v2.btag.csv",
        #"BTagSF * ./data/DeepCSV_94XSF_V4_B_F.btag.csv"
        "corrections" : [
            #"el_triggerSF ele28_ht150_OR_ele32_ele_pt_ele_sceta ./data/SingleEG_JetHT_Trigger_Scale_Factors_ttHbb2017_v3.histo.root",
            "el_triggerSF SFs_ele_pt_ele_sceta_ele28_ht150_OR_ele35_2017BCDEF ./data/SingleEG_JetHT_Trigger_Scale_Factors_ttHbb_Data_MC_v5.0.histo.root",
            "el_recoSF EGamma_SF2D ./data/egammaEffi_EGM2D_runBCDEF_passingRECO_v2.histo.root",
            "el_idSF EGamma_SF2D ./data/2017_ElectronTight.histo.root",
            "mu_triggerSF IsoMu27_PtEtaBins/pt_abseta_ratio ./data/EfficienciesAndSF_RunBtoF_Nov17Nov2017.histo.root",
            "mu_isoSF NUM_TightRelIso_DEN_TightIDandIPCut_pt_abseta ./data/RunBCDEF_SF_ISO.histo.root",
            "mu_idSF NUM_TightID_DEN_genTracks_pt_abseta ./data/RunBCDEF_SF_ID.histo.root",
            #"BTagSF * ./data/DeepCSV_94XSF_V5_B_F.btag.csv"
            #"BTagSF * ./data/deepCSV_sfs_v2.btag.csv"
        ],
        "btagging algorithm" : "btagDeepFlavB",
        "btagging WP" : 
            {"btagDeepB": 0.4941, # medium working point for btagDeepB
            "btagCSVV2": 0.8484, # medium working point for btagCSVV2
            "btagDeepFlavB": 0.3033 # medium working point for btagDeepFlavB
            },
        "bbtagging WP" : 0.8, # medium 2 working point for DeepDoubleB tagger
    }

}


#################################### Samples info ##############################################################################

dataset = "nanoAODv5_central"

genweights = {
    "maren": {
        "ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8": 4163245.9264759924,
        "TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8": 32426751447.698845,
        "ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8": 4371809.996849993,
        "TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8": 4720387516.446639,
        "TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8": 27550924865.573532,
    },
    "maren_v2":{
        "ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8": 4163307.8224659907,
        "TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8": 30587299080.771355,
        "ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8": 4388463.910001993,
        "TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8": 4723736912.791826,
        "TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8": 27606592686.468067,
    },
    "nanoAOD_central":{
        "ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8": 4216319.315883999,
        "TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8": 720253370.0403845, #not full statistics
        "ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8": 5722756.565262001,
        "TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8": 283000430.5968169, #not full statistics
        "TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8": 1647945788.3386502, #not full statistics
    },
    "nanoAODv5_central":{
        "ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8": 4216319.315883999,
        "ttHTobb_ttToSemiLep_M125_TuneCP5_13TeV-powheg-pythia8": 2215145.8533389997,
        "TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8": 33091176613.77194,
        "ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8": 4484065.542378,
        "TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8": 4980769113.241218, 
        "TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8": 40821660261.670876, 
        "ST_s-channel_4f_leptonDecays_TuneCP5_PSweights_13TeV-amcatnlo-pythia8": 37052021.59459843,
        "ST_t-channel_antitop_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8": 3675910.0,
        "ST_t-channel_top_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8": 5982064.0,
        "ST_tW_antitop_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8": 270762750.1725248,
        "ST_tW_top_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8": 277241050.84022206,
        "TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8": 560315.1334199999,
        "TTWJetsToLNu_TuneCP5_PSweights_13TeV-amcatnloFXFX-madspin-pythia8": 1690120.2450226927,
        "TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8": 383062.06864380004,
        "TTZToLLNuNu_M-10_TuneCP5_PSweights_13TeV-amcatnlo-pythia8": 2694672.7126361188,
        #"WJetsToLNu_TuneCP5_13TeV-madgraphMLM-pythia8":  29981320.0,
        "WJetsToLNu_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 11026234235687.748,
        "WJetsToLNu_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 4064208918856.2876,
        "WJetsToLNu_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 2429846590795.5117,
        "DYJetsToLL_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 533210706325.52826,
        "DYJetsToLL_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 445782009508.43427,
        "DYJetsToLL_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8": 142389472522.05267,
        "WW_TuneCP5_13TeV-pythia8": 7765891.020262634,
        "WZ_TuneCP5_13TeV-pythia8": 3928630.0,
        "ZZ_TuneCP5_13TeV-pythia8": 1949768.0,
    },
}

samples_info = {
    "ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8": {
            "process": "ttHTobb",
            "XS": 0.2934045,
            "ngen_weight": genweights[dataset]["ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8"],
            },
    "ttHTobb_ttToSemiLep_M125_TuneCP5_13TeV-powheg-pythia8": {
            "process": "ttHTobb",
            "XS": 0.1289155939,
            "ngen_weight": genweights[dataset]["ttHTobb_ttToSemiLep_M125_TuneCP5_13TeV-powheg-pythia8"],
            },
    "TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8": {
            "XS": 365.45736135,
            "ngen_weight": genweights[dataset]["TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8"],
            },
    "ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8": {
            "process": "ttHToNonbb",
            "XS": 0.2150955,
            "ngen_weight": genweights[dataset]["ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8"],
            },
    "TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8": {
            "XS": 88.341903326,
            "ngen_weight": genweights[dataset]["TTTo2L2Nu_TuneCP5_PSweights_13TeV-powheg-pythia8"],
            },
    "TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8": {
            "XS": 377.9607353256,
            "ngen_weight": genweights[dataset]["TTToHadronic_TuneCP5_PSweights_13TeV-powheg-pythia8"],
            },
    #"ST_s-channel_4f_leptonDecays_TuneCP5_PSweights_13TeV-amcatnlo-pythia8": {
    #        "process": "singlet",
    #        "XS": 3.36,
    #        "ngen_weight": genweights[dataset]["ST_s-channel_4f_leptonDecays_TuneCP5_PSweights_13TeV-amcatnlo-pythia8"],
    #        },
    #"ST_t-channel_antitop_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8": {
    #        "process": "singlet",
    #        "XS": 80.95,
    #        "ngen_weight": genweights[dataset]["ST_t-channel_antitop_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8"],
    #        },
    #"ST_t-channel_top_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8": {
    #        "process": "singlet",
    #        "XS": 136.02,
    #        "ngen_weight": genweights[dataset]["ST_t-channel_top_4f_inclusiveDecays_TuneCP5_13TeV-powhegV2-madspin-pythia8"],
    #        },
    #"ST_tW_antitop_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8": {
    #        "process": "singlet",
    #        "XS": 35.85,
    #        "ngen_weight": genweights[dataset]["ST_tW_antitop_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8"],
    #        },
    #"ST_tW_top_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8": {
    #        "process": "singlet",
    #        "XS": 35.85,
    #        "ngen_weight": genweights[dataset]["ST_tW_top_5f_inclusiveDecays_TuneCP5_PSweights_13TeV-powheg-pythia8"],
    #        },
    #"TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8": {
    #        "process": "ttv",
    #        "XS": 0.3708,
    #        "ngen_weight": genweights[dataset]["TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8"],
    #        },
    #"TTWJetsToLNu_TuneCP5_PSweights_13TeV-amcatnloFXFX-madspin-pythia8": {
    #        "process": "ttv",
    #        "XS": 0.1792,
    #        "ngen_weight": genweights[dataset]["TTWJetsToLNu_TuneCP5_PSweights_13TeV-amcatnloFXFX-madspin-pythia8"],
    #        },
    #"TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8": {
    #        "process": "ttv",
    #        "XS": 0.6012,
    #        "ngen_weight": genweights[dataset]["TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8"],
    #        },
    #"TTZToLLNuNu_M-10_TuneCP5_PSweights_13TeV-amcatnlo-pythia8": {
    #        "process": "ttv",
    #        "XS": 0.2589,
    #        "ngen_weight": genweights[dataset]["TTZToLLNuNu_M-10_TuneCP5_PSweights_13TeV-amcatnlo-pythia8"],
    #        },
    #"WJetsToLNu_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 50131.98,
    #        "ngen_weight": genweights[dataset]["WJetsToLNu_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"WJetsToLNu_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 8426.09,
    #        "ngen_weight": genweights[dataset]["WJetsToLNu_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"WJetsToLNu_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 3172.96,
    #        "ngen_weight": genweights[dataset]["WJetsToLNu_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"DYJetsToLL_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 4620.52,
    #        "ngen_weight": genweights[dataset]["DYJetsToLL_0J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"DYJetsToLL_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 859.59,
    #        "ngen_weight": genweights[dataset]["DYJetsToLL_1J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"DYJetsToLL_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8": {
    #        "process": "vjets",
    #        "XS": 338.26,
    #        "ngen_weight": genweights[dataset]["DYJetsToLL_2J_TuneCP5_13TeV-amcatnloFXFX-pythia8"],
    #        },
    #"WW_TuneCP5_13TeV-pythia8": {
    #        "process": "diboson",
    #        "XS": 118.7,
    #        "ngen_weight": genweights[dataset]["WW_TuneCP5_13TeV-pythia8"],
    #        },
    #"WZ_TuneCP5_13TeV-pythia8": {
    #        "process": "diboson",
    #        "XS": 65.5443,
    #        "ngen_weight": genweights[dataset]["WZ_TuneCP5_13TeV-pythia8"],
    #        },
    #"ZZ_TuneCP5_13TeV-pythia8": {
    #        "process": "diboson",
    #        "XS": 15.8274,
    #        "ngen_weight": genweights[dataset]["ZZ_TuneCP5_13TeV-pythia8"],
    #        },
}


############################################################### Histograms ########################################################

histogram_settings = {

    "njets" : (0,14,15),
    "nleps" : (0,10,11),
    "btags" : (0,8,9),
    "pu_weights" : (0,4,21),
    "btag_weights" : (0,2,50),
    "leading_jet_pt" : (0,500,31),
    "leading_jet_pt_nom" : (0,500,31),
    "leading_jet_eta" : (-2.4,2.4,31),
    "leading_jet_phi" : (-3.14,3.14,31),
    "leading_jet_mass" : (0,300,31),
    "leading_jet_btagDeepFlavB" : (0,1,31),
    "leading_lepton_pt" : (0,500,31),
    "leading_lepton_eta" : (-2.4,2.4,31),
    "leading_lepton_phi" : (-3.14,3.14,31),
    "leading_lepton_mass" : (0,300,31),
    "leading_bjet_pt" : (0,500,31),
    "leading_bjet_pt_nom" : (0,500,31),
    "leading_bjet_eta" : (-2.4,2.4,31),
    "subleading_bjet_pt" : (0,500,31),
    "subleading_bjet_pt_nom" : (0,500,31),
    "subleading_bjet_eta" : (-2.4,2.4,31),

    "subleading_jet_pt" : (0,500,31),
    "subleading_jet_pt_nom" : (0,500,31),
    "subleading_jet_eta" : (-2.4,2.4,31),
    "subleading_jet_phi" : (-3.14,3.14,31),
    "subleading_jet_mass" : (0,300,31),
    "subleading_jet_btagDeepFlavB" : (0,1,31),
    
    "third_jet_pt" : (0,500,31),
    "third_jet_pt_nom" : (0,500,31),
    "third_jet_eta" : (-2.4,2.4,31),
    "third_jet_phi" : (-3.14,3.14,31),
    "third_jet_mass" : (0,300,31),
    "third_jet_btagDeepFlavB" : (0,1,31),
    
    "fourth_jet_pt" : (0,500,31),
    "fourth_jet_pt_nom" : (0,500,31),
    "fourth_jet_eta" : (-2.4,2.4,31),
    "fourth_jet_phi" : (-3.14,3.14,31),
    "fourth_jet_mass" : (0,300,31),
    "fourth_jet_btagDeepFlavB" : (0,1,31),
    
    "fifth_jet_pt" : (0,500,31),
    "fifth_jet_pt_nom" : (0,500,31),
    "fifth_jet_eta" : (-2.4,2.4,31),
    "fifth_jet_phi" : (-3.14,3.14,31),
    "fifth_jet_mass" : (0,300,31),
    "fifth_jet_btagDeepFlavB" : (0,1,31),
    
    "sixth_jet_pt" : (0,500,31),
    "sixth_jet_pt_nom" : (0,500,31),
    "sixth_jet_eta" : (-2.4,2.4,31),
    "sixth_jet_phi" : (-3.14,3.14,31),
    "sixth_jet_mass" : (0,300,31),
    "sixth_jet_btagDeepFlavB" : (0,1,31),
    
    "seventh_jet_pt" : (0,500,31),
    "seventh_jet_pt_nom" : (0,500,31),
    "seventh_jet_eta" : (-2.4,2.4,31),
    "seventh_jet_phi" : (-3.14,3.14,31),
    "seventh_jet_mass" : (0,300,31),
    "seventh_jet_btagDeepFlavB" : (0,1,31),
    
    "eighth_jet_pt" : (0,500,31),
    "eighth_jet_pt_nom" : (0,500,31),
    "eighth_jet_eta" : (-2.4,2.4,31),
    "eighth_jet_phi" : (-3.14,3.14,31),
    "eighth_jet_mass" : (0,300,31),
    "eighth_jet_btagDeepFlavB" : (0,1,31),
    
    "ninth_jet_pt" : (0,500,31),
    "ninth_jet_pt_nom" : (0,500,31),
    "ninth_jet_eta" : (-2.4,2.4,31),
    "ninth_jet_phi" : (-3.14,3.14,31),
    "ninth_jet_mass" : (0,300,31),
    "ninth_jet_btagDeepFlavB" : (0,1,31),
    
    "tenth_jet_pt" : (0,500,31),
    "tenth_jet_pt_nom" : (0,500,31),
    "tenth_jet_eta" : (-2.4,2.4,31),
    "tenth_jet_phi" : (-3.14,3.14,31),
    "tenth_jet_mass" : (0,300,31),
    "tenth_jet_btagDeepFlavB" : (0,1,31),
    
    "MET_pt" : (0,500,31),
    "MET_phi" : (-3.14,3.14,31),
    "MET_sumEt" : (0, 300,31),

    "higgs_pt": (0,500,31),
    "higgs_eta": (-2.4,2.4,31),
    "top_pt" : (0,500,31),
    "top_eta": (-2.4,2.4,31),
    "nfatjets": (0,5,6),
    "nbbtags": (0,4,5),
    "ntop_candidates": (0,5,6),
    "nWH_candidates": (0,5,6),
    "leading_fatjet_pt": (200,500,31),
    "leading_fatjet_eta": (-2.4,2.4,31),
    "leading_fatjet_mass": (0,300,31),
    "leading_fatjet_SDmass": (0,300,31),
    "subleading_fatjet_pt": (200,500,31),
    "subleading_fatjet_mass": (0,300,31),
    "subleading_fatjet_SDmass": (0,300,31),
    "leading_WHcandidate_SDmass": (0,300,31),
    "leading_topcandidate_SDmass": (0,300,31),
    "tau32_fatjets": (0,1,31),
    "tau32_topcandidates": (0,1,31),
    "tau32_WHcandidates": (0,1,31),
    "tau21_fatjets": (0,1,31),
    "tau21_topcandidates": (0,1,31),
    "tau21_WHcandidates": (0,1,31)
}
