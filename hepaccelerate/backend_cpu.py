import os
import numba
import numpy as np
import math

@numba.jit(fastmath=True)
def searchsorted_devfunc(arr, val):
    ret = -1
    for i in range(len(arr)):
        #if val <= arr[i]:
        if val < arr[i+1]:
            ret = i
            break
    return ret

@numba.jit(fastmath=True)
def searchsorted_devfunc2D(arr_x, arr_y, val_x, val_y):
    ret = -1
    for i in range(len(arr_x)):
        for j in range(len(arr_y)):
            #if val <= arr[i]:
            if val_x < arr_x[i+1] and val_y <arr_y[i+1]:
                ret_i = i
                ret_j = j
                break
    return ret_i, ret_j

#need atomics to add to bin contents
@numba.jit
def fill_histogram(data, weights, bins, out_w, out_w2):
    for i in range(len(data)):
        bin_idx = searchsorted_devfunc(bins, data[i])
        if bin_idx >=0 and bin_idx < len(out_w):
            out_w[bin_idx] += weights[i]
            out_w2[bin_idx] += weights[i]**2

@numba.njit(parallel=True)
def select_opposite_sign_muons_kernel(muon_charges_content, muon_charges_offsets, content_mask_in, content_mask_out):
    
    for iev in numba.prange(muon_charges_offsets.shape[0]-1):
        start = muon_charges_offsets[iev]
        end = muon_charges_offsets[iev + 1]
        
        ch1 = 0
        idx1 = -1
        ch2 = 0
        idx2 = -1
        
        for imuon in range(start, end):
            if not content_mask_in[imuon]:
                continue
                
            if idx1 == -1:
                ch1 = muon_charges_content[imuon]
                idx1 = imuon
                continue
            else:
                ch2 = muon_charges_content[imuon]
                if (ch2 != ch1):
                    idx2 = imuon
                    content_mask_out[idx1] = 1
                    content_mask_out[idx2] = 1
                    break
    return

@numba.njit(parallel=True)
def sum_in_offsets_kernel(content, offsets, mask_rows, mask_content, out):

    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
            
        start = offsets[iev]
        end = offsets[iev + 1]
        for ielem in range(start, end):
            if mask_content[ielem]:
                out[iev] += content[ielem]

@numba.njit(parallel=True)
def multiply_in_offsets_kernel(content, offsets, mask_rows, mask_content, out):

    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue

        start = offsets[iev]
        end = offsets[iev + 1]
        for ielem in range(start, end):
            if mask_content[ielem]:
                out[iev] *= content[ielem]    
       
 
@numba.njit(parallel=True)
def max_in_offsets_kernel(content, offsets, mask_rows, mask_content, out):

    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
            
        start = offsets[iev]
        end = offsets[iev + 1]
    
        first = True
        accum = 0
        
        for ielem in range(start, end):
            if mask_content[ielem]:
                if first or content[ielem] > accum:
                    accum = content[ielem]
                    first = False
        out[iev] = accum

        
@numba.njit(parallel=True)
def min_in_offsets_kernel(content, offsets, mask_rows, mask_content, out):

    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
            
        start = offsets[iev]
        end = offsets[iev + 1]
    
        first = True
        accum = 0
        
        for ielem in range(start, end):
            if mask_content[ielem]:
                if first or content[ielem] < accum:
                    accum = content[ielem]
                    first = False
        out[iev] = accum

@numba.njit(parallel=True)
def dnn_jets_kernel(content, offsets, feats_indx, nobj, mask_rows, mask_content, out):
    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
        start = offsets[iev]
        end = offsets[iev + 1]

        for idx in range(nobj):
            index_to_get = 0
            for ielem in range(start, end):
                if mask_content[ielem]:
                    if index_to_get == idx:
                        out[iev][idx][feats_indx] = content[ielem]
                        break
                    else:
                        index_to_get += 1

@numba.njit(parallel=True)
def dnn_met_kernel(content, feats_indx, mask_rows, out):
    for iev in numba.prange(content.shape[0]-1):
        if not mask_rows[iev]:
            continue

        out[iev][feats_indx] = content[iev]


@numba.njit(parallel=True)
def dnn_leps_kernel(content, feats_indx, mask_rows, out):
    for iev in numba.prange(content.shape[0]-1):
        if not mask_rows[iev]:
            continue

        out[iev][0][feats_indx] = content[iev]


@numba.njit(parallel=True)
def calc_px_kernel(content_pt, content_phi, out):
    for iobj in numba.prange(content_pt.shape[0]-1):
        out[iobj] = content_pt[iobj] * np.cos(content_phi[iobj])

@numba.njit(parallel=True)
def calc_py_kernel(content_pt, content_phi, out):
    for iobj in numba.prange(content_pt.shape[0]-1):
        out[iobj] = content_pt[iobj] * np.sin(content_phi[iobj])

@numba.njit(parallel=True)
def calc_pz_kernel(content_pt, content_eta, out):
    for iobj in numba.prange(content_pt.shape[0]-1):
        out[iobj] = content_pt[iobj] * np.sinh(content_eta[iobj])

@numba.njit(parallel=True)
def calc_en_kernel(content_pt, content_eta, content_mass, out):
    for iobj in numba.prange(content_pt.shape[0]-1):
        out[iobj] = np.sqrt(content_mass[iobj]**2 + (1+np.sinh(content_eta[iobj])**2)*content_pt[iobj]**2)
    
@numba.njit(parallel=True)
def get_in_offsets_kernel(content, offsets, indices, mask_rows, mask_content, out):
    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
        start = offsets[iev]
        end = offsets[iev + 1]

        index_to_get = 0
        for ielem in range(start, end):
            if mask_content[ielem]:
                if index_to_get == indices[iev]:
                    out[iev] = content[ielem]
                    break
                else:
                    index_to_get += 1
        
@numba.njit(parallel=True)
def min_in_offsets_kernel(content, offsets, mask_rows, mask_content, out):
    for iev in numba.prange(offsets.shape[0]-1):
        if not mask_rows[iev]:
            continue
            
        start = offsets[iev]
        end = offsets[iev + 1]
    
        first = True
        accum = 0
        
        for ielem in range(start, end):
            if mask_content[ielem]:
                if first or content[ielem] < accum:
                    accum = content[ielem]
                    first = False
        out[iev] = accum

@numba.jit
def stack_arrays_kernel(arr, dim):
    tiled = np.stack(tuple(arr), axis = -1)
    tiled = np.reshape(tiled, dim)
    return tiled
        
def sum_in_offsets(struct, content, mask_rows, mask_content, dtype=None):
    if not dtype:
        dtype = content.dtype
    sum_offsets = np.zeros(len(struct.offsets) - 1, dtype=dtype)
    sum_in_offsets_kernel(content, struct.offsets, mask_rows, mask_content, sum_offsets)
    return sum_offsets

def multiply_in_offsets(struct, content, mask_rows, mask_content, dtype=None):
    if not dtype:
        dtype = content.dtype
    product_offsets = np.ones(len(struct.offsets) - 1, dtype=dtype)
    multiply_in_offsets_kernel(content, struct.offsets, mask_rows, mask_content, product_offsets)
    return product_offsets

def max_in_offsets(struct, content, mask_rows, mask_content):
    max_offsets = np.zeros(len(struct.offsets) - 1, dtype=content.dtype)
    max_in_offsets_kernel(content, struct.offsets, mask_rows, mask_content, max_offsets)
    return max_offsets

def min_in_offsets(struct, content, mask_rows, mask_content):
    max_offsets = np.zeros(len(struct.offsets) - 1, dtype=content.dtype)
    min_in_offsets_kernel(content, struct.offsets, mask_rows, mask_content, max_offsets)
    return max_offsets

def select_muons_opposite_sign(muons, in_mask):
    out_mask = np.invert(muons.make_mask())
    select_opposite_sign_muons_kernel(muons.charge, muons.offsets, in_mask, out_mask)
    return out_mask

def get_in_offsets(content, offsets, indices, mask_rows, mask_content):
    out = np.zeros(len(offsets) - 1, dtype=content.dtype)
    get_in_offsets_kernel(content, offsets, indices, mask_rows, mask_content, out)
    return out

def calc_px(content_pt, content_phi):
    out = np.zeros(content_pt.shape[0]-1, dtype=content_pt.dtype)
    calc_px_kernel(content_pt, content_phi, out)
    return out

def calc_py(content_pt, content_phi):
    out = np.zeros(content_pt.shape[0]-1, dtype=content_pt.dtype)
    calc_py_kernel(content_pt, content_phi, out)
    return out

def calc_pz(content_pt, content_eta):
    out = np.zeros(content_pt.shape[0]-1, dtype=content_pt.dtype)
    calc_pz_kernel(content_pt, content_eta, out)
    return out

def calc_en(content_pt, content_eta, content_mass):
    out = np.zeros(content_pt.shape[0]-1, dtype=content_pt.dtype)
    calc_en_kernel(content_pt, content_eta, content_mass, out)
    return out


# functions preparing inputs for COBRA DNN architecture (not nice, but it works!!!)
def make_jets_inputs(content, offsets, nobj, feats, mask_rows, mask_content):
    
    out = np.zeros((len(offsets) - 1, nobj, len(feats)), dtype=np.float32)
    for f in feats:
        if f == "px":
            feature = calc_px(content.pt, content.phi)
        elif f == "py":
            feature = calc_py(content.pt, content.phi)
        elif f == "pz":
            feature = calc_pz(content.pt, content.eta)
        elif f == "en":
            feature = calc_en(content.pt, content.eta, content.mass)
        else:
            feature = getattr(content, f) 
        dnn_jets_kernel(feature, offsets, feats.index(f), nobj, mask_rows, mask_content, out)
    return out

def make_leps_inputs(electrons, muons, numEvents, feats, mask_rows, el_mask_content, mu_mask_content):

    inds = np.zeros(numEvents, dtype=np.int32)

    feature = {}
    feature["pt"] = get_in_offsets(muons.pt, muons.offsets, inds, mask_rows, mu_mask_content) + get_in_offsets(electrons.pt, electrons.offsets, inds, mask_rows, el_mask_content)
    feature["eta"] = get_in_offsets(muons.eta, muons.offsets, inds, mask_rows, mu_mask_content) + get_in_offsets(electrons.eta, electrons.offsets, inds, mask_rows, el_mask_content)
    feature["phi"] = get_in_offsets(muons.phi, muons.offsets, inds, mask_rows, mu_mask_content) + get_in_offsets(electrons.phi, electrons.offsets, inds, mask_rows, el_mask_content)
    feature["mass"] = get_in_offsets(muons.mass, muons.offsets, inds, mask_rows, mu_mask_content) + get_in_offsets(electrons.mass, electrons.offsets, inds, mask_rows, el_mask_content)

    out = np.zeros((numEvents, 1, len(feats)), dtype=np.float32)
    for f in feats:
        if f == "px":
            feature["px"] = calc_px(feature["pt"], feature["phi"])
        elif f == "py":
            feature["py"] = calc_py(feature["pt"], feature["phi"])
        elif f == "pz":
            feature["pz"] = calc_pz(feature["pt"], feature["eta"])
        elif f == "en":
            feature["en"] = calc_en(feature["pt"], feature["eta"], feature["mass"])
        dnn_leps_kernel(feature[f], feats.index(f), mask_rows, out)
    return out

def make_met_inputs(content, numEvents, feats, mask_rows):

    out = np.zeros((numEvents, len(feats)), dtype=np.float32)
    for f in feats:
        if f == "px":
            feature = calc_px(content["MET_pt"], content["MET_phi"])
        elif f == "py":
            feature = calc_py(content["MET_pt"], content["MET_phi"])
        else:
            feature = content["MET_" + f]
        dnn_met_kernel(feature, feats.index(f), mask_rows, out)
    return out

"""
For all events (N), mask the objects in the first collection (M1) if they are closer than dr2 to any object in the second collection (M2).

    etas1: etas of the first object, array of (M1, )
    phis1: phis of the first object, array of (M1, )
    mask1: mask (enabled) of the first object, array of (M1, )
    offsets1: offsets of the first object, array of (N, )

    etas2: etas of the second object, array of (M2, )
    phis2: phis of the second object, array of (M2, )
    mask2: mask (enabled) of the second object, array of (M2, )
    offsets2: offsets of the second object, array of (N, )
    
    mask_out: output mask, array of (M1, )

"""
@numba.njit(parallel=True)
def get_lepton_SF_kernel(el_pt, el_eta, mu_pt, mu_eta, pdg_id, evaluator, name, out):
    
    for iev in numba.prange(len(var_x)):
        if pdg_id == 11:
           out[iev] = evaluator["el_"+name](el_pt[iev], el_eta[iev]) 
        if pdg_id == 13:
           out[iev] = evaluator["mu_"+name](mu_pt[iev], mu_eta[iev]) 
            

@numba.njit(parallel=True)
def mask_deltar_first_kernel(etas1, phis1, mask1, offsets1, etas2, phis2, mask2, offsets2, dr2, mask_out):
    
    for iev in numba.prange(len(offsets1)-1):
        a1 = offsets1[iev]
        b1 = offsets1[iev+1]
        
        a2 = offsets2[iev]
        b2 = offsets2[iev+1]
        
        for idx1 in range(a1, b1):
            if not mask1[idx1]:
                continue
                
            eta1 = etas1[idx1]
            phi1 = phis1[idx1]
            for idx2 in range(a2, b2):
                if not mask2[idx2]:
                    continue
                eta2 = etas2[idx2]
                phi2 = phis2[idx2]
                
                deta = abs(eta1 - eta2)
                dphi = (phi1 - phi2 + math.pi) % (2*math.pi) - math.pi
                
                #if first object is closer than dr2, mask element will be *disabled*
                passdr = ((deta**2 + dphi**2) < dr2)
                mask_out[idx1] = mask_out[idx1] | passdr
                
def mask_deltar_first(objs1, mask1, objs2, mask2, drcut):
    assert(mask1.shape == objs1.eta.shape)
    assert(mask2.shape == objs2.eta.shape)
    assert(objs1.offsets.shape == objs2.offsets.shape)
    
    mask_out = np.zeros_like(objs1.eta, dtype=np.bool)
    mask_deltar_first_kernel(
        objs1.eta, objs1.phi, mask1, objs1.offsets,
        objs2.eta, objs2.phi, mask2, objs2.offsets,
        drcut**2, mask_out
    )
    mask_out = np.invert(mask_out)
    return mask_out

def histogram_from_vector(data, weights, bins):        
    out_w = np.zeros(len(bins) - 1, dtype=np.float64)
    out_w2 = np.zeros(len(bins) - 1, dtype=np.float64)
    fill_histogram(data, weights, bins, out_w, out_w2)
    return out_w, out_w2, bins
    
@numba.njit(parallel=True)
def get_bin_contents_kernel(values, edges, contents, out):
    for i in numba.prange(len(values)):
        v = values[i]
        ibin = searchsorted_devfunc(edges, v)
        if ibin>=0 and ibin < len(contents):
            out[i] = contents[ibin]

def get_bin_contents(values, edges, contents, out):
    assert(values.shape == out.shape)
    assert(edges.shape[0] == contents.shape[0]+1)
    get_bin_contents_kernel(values, edges, contents, out)

def get_lepton_SF(el_pt, el_eta, mu_pt, mu_eta, pdg_id, evaluator, name):
    out = np.zeros(len(pdg_id), dtype=np.float32) 
    get_lepton_SF_kernel(el_pt, el_eta, mu_pt, mu_eta, pdg_id, evaluator, name, out)
    return out
