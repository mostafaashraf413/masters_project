#from deap import base, creator
import random
from deap import tools
import numpy as np
import utils
import ga_nmf_base as ga
#from scipy.stats import levy_stable as levys
from scipy.special import gamma
from math import sin, pi

dataset = ('movelens 100k', '../resources/ml-100k/final_set.csv')
#dataset = ('movelens 1m', '../resources/ml-1m/ratings.dat')
train, test, mSize = utils.read_data_to_train_test(dataset[1], zero_index = False)

V = utils.create_matrix(train, mSize)
maskV = np.sign(V)

r_dim = 20
eps = 1e-20

def generate_ind():
    r = np.random.rand(r_dim)
    #r = np.random.normal(scale=1./r_dim, size = r_dim)
    #r = np.maximum(r, eps)
    return r
      
def evaluate_ind(ind):
    W, H = ind[:mSize[0]], ind[mSize[0]:]
    predV = maskV * W.dot(H.T)
    fit = utils.rmse(V, predV, len(train))#np.linalg.norm(V-predV)
    
    #if np.min(ind)<0:
    #    fit *= 100
    return fit,
    
def mCX_single(ind1, ind2):
    cX_point = random.randint(1,len(ind1))
    ind1[:,:cX_point], ind2[:,:cX_point] = ind2[:,:cX_point].copy(), ind1[:,:cX_point].copy()
    return ind1, ind2

def mCX_double_vertically(ind1, ind2):
    cX_point_1 = random.randint(0,len(ind1[0])-1)
    cX_point_2 = random.randint(0,len(ind1[0]))
    
    if cX_point_1 == cX_point_2:
        cX_point_2 += 1
    elif cX_point_1 > cX_point_2:
        cX_point_1, cX_point_2 = cX_point_2, cX_point_1
        
    ind1[:,cX_point_1:cX_point_2], ind2[:,cX_point_1:cX_point_2] = ind2[:,cX_point_1:cX_point_2].copy(), ind1[:,cX_point_1:cX_point_2].copy()
    return ind1, ind2
    
def mCX_double_horizontally(ind1, ind2):
    cX_point_1 = random.randint(0,len(ind1)-1)
    cX_point_2 = random.randint(0,len(ind1))
    
    if cX_point_1 == cX_point_2:
        cX_point_2 += 1
    elif cX_point_1 > cX_point_2:
        cX_point_1, cX_point_2 = cX_point_2, cX_point_1
        
    ind1[cX_point_1:cX_point_2], ind2[cX_point_1:cX_point_2] = ind2[cX_point_1:cX_point_2].copy(), ind1[cX_point_1:cX_point_2].copy()
    return ind1, ind2
    
def mCV_swaping_matrices(ind1, ind2):
    ind1[:mSize[0]], ind2[:mSize[0]] = ind2[:mSize[0]].copy(), ind1[:mSize[0]].copy()
    return ind1, ind2
        
def linear_combinaiton_CX(ind1, ind2):
    rand1, rand2= random.random(), random.random()
    rand1_c, rand2_c = 1-rand1, 1-rand2
    
    ind1[:], ind2[:] = (ind1.copy()*rand1 + ind2.copy()*rand1_c), (ind1.copy()*rand2 + ind2.copy()*rand2_c)
    return ind1, ind2
    
def mMut(ind, indpb):
    mu=0
    sigma=1
    tools.mutGaussian(ind, mu, sigma, indpb)
    ind = np.maximum(ind, eps)
    return ind

def mixMut(ind, indpb):
    if random.random() < 0.5:
        return levyMut(ind, indpb)
    return mMut(ind, indpb)

##############################################
sigma = None
def mantegna_levy_step(beta=1.5, size=1):
    global sigma
    if sigma == None:
        sigma = gamma(1+beta) * sin(pi*beta/2.)
        sigma /= ( beta * gamma((1+beta)/2) * pow(2, (beta-1)/2.) )
        sigma = pow(sigma , 1./beta)
    u = np.random.normal(scale=sigma, size=size)
    v = np.absolute(np.random.normal(size=size))
    step = u/np.power(v, 1./beta)
    
    return step
###############################################
    
def levyMut(ind_, indpb=0.1):
    ind = ind_.copy()
    steps = mantegna_levy_step(size=(ind.shape)) 
    
    levy = 1.5*gamma(1.5)*sin(pi*1.5/2)/(pi*np.power(steps, 2))
    
    ind += 0.2 * levy
    
    if evaluate_ind(ind) < evaluate_ind(ind_):
        ind_[:] = ind[:]
    
    return ind

def least_square_LS(ind):
    #ind[:mSize[0]] = np.linalg.lstsq(ind[mSize[0]:].T, V)[0]
    ind[mSize[0]:] = np.linalg.lstsq(ind[:mSize[0]], V)[0].T
    return ind

def wnmf_LS(ind):
    beta = 1
    W, H = ind[:mSize[0]], ind[mSize[0]:].T
    
    VH = np.dot(V, H.T)
    WHH = np.dot(maskV*W.dot(H), H.T)+eps
    W[:] = W * ((1-beta)+beta*(VH/WHH))
    W[:] = np.maximum(W, eps)
    
    WV = np.dot(W.T, V)
    WWH = np.dot(W.T, maskV*W.dot(H))+eps
    H[:] = H * ((1-beta)+beta*(WV/WWH))
    H[:] = np.maximum(H, eps)
    
    return ind
    
########################################################################################
#"Koren, Yehuda, Robert Bell, and Chris Volinsky. "Matrix factorization techniques 
# for recommender systems." Computer 42.8 (2009)."    
def sgd_LS(ind):
    #rf=0.1
    lr=0.006
    W, H = ind[:mSize[0]], ind[mSize[0]:]
    for u,i,y in [[td[0], td[1], td[2]] for td in  train]:                                       
        e = y - np.dot(W[u], H[i].T)
        W[u] += lr*(e * H[i] )#- (rf*W[u]))
        H[i] += lr*(e * W[u] )#- (rf*H[i]))
    return ind
        
if __name__ == '__main__':
    
    pop_size = 50
    mate = linear_combinaiton_CX
    mutate = mMut
    MUTPB = 0.1
    local_search = levyMut
    CXPB = 0.9
    LSPB = 0.9
    new_inds_ratio = 0.25
    NGEN = 100
    method_name = 'GA_LS-beta=1'
  
    pop = ga.run_ga(ind_size = mSize[0]+mSize[1], pop_size = pop_size, mate = mate, mutate = mutate, MUTPB = MUTPB, 
                    evaluate = evaluate_ind, local_search = local_search, CXPB = CXPB, LSPB = LSPB,
                    ind_gen = generate_ind, new_inds_ratio = new_inds_ratio, NGEN = NGEN, curve_label = method_name)
   
    #printng results:
    minInd = min(pop , key = lambda ind: ind.fitness.values[0])
    W, H = minInd[:mSize[0]], minInd[mSize[0]:].T
    ga_results = utils.print_results(uMat = W, iMat = H, nFeatures = r_dim, 
                                    train_data = train, test_data = test, 
                                    method_name = method_name, nIterations = NGEN, 
                                    dataset_name = dataset[0], 
                                    method_details = [('pop_size',pop_size),
                                        ('crossover', mate.__name__),
                                        ('crossover prob', CXPB),
                                        ('mutation',mutate.__name__),
                                        ('mutation prob', MUTPB),
                                        ('local search', local_search.__name__),
                                        ('local search prob', LSPB),
                                        ('new random individuals ratio', new_inds_ratio)]
                                    )