
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
import statistics
from math import log
import time
from utils import vector_to_dict

'''
SYNCH. DIST AVG
1) Find optimal alpha
2) Set up W matrix
3) Set x(k-1) = x(0) for algorithm start
4) While e(k) > epsilon:
    x(k) = W*x(k-1)
    e(k) = || . ||
    x(k-1) = x(k)
TRANSMISSIONS: for each iteration, transmissions increase by the number of edges in the graph
Notice: W works on every entry in x(0) at each iteration, every link is active at each iteration -- confirm numerically
'''
def dist_avg_synch(graph, TOL):
    print("")
    print("------- SYNCH. DIST. AVG. ------- ")
    start_time = time.time()
    
    # Find optimal alpha
    all_nodes = list(nx.nodes(graph))

    laplacian = nx.laplacian_matrix(graph).toarray()
    eigenvalues = np.linalg.eigvals(laplacian)
    eigenvalues_list = eigenvalues.tolist()

    eigenvalues_list.sort(reverse=True)                 # sort in decending order to get eig1 and eigN-1
    alpha_opt = 2 / (eigenvalues_list[0] + eigenvalues_list[-2])
    
    # Set up W matrix
    W = np.zeros((len(all_nodes), len(all_nodes)))
    W = np.eye(len(all_nodes)) - alpha_opt * laplacian

    num_edges = np.count_nonzero(np.triu(W, k=1))

    row_sums = np.sum(W, axis=1)
    col_sums = np.sum(W, axis=0)
    if not np.allclose(row_sums, 1) or not np.allclose(col_sums, 1):
        print("\033[91mERROR: The sum of rows or columns in W does not equal 1.\033[0m")
    elif not np.allclose(W, W.T):
        print("\033[91mERROR: W is not symmetric.\033[0m")

    # Set x(k-1) = x(0) for algorithm start
    x_kminus1 = np.array(list(nx.get_node_attributes(graph, "temp").values()))   

    # get required true average needed for the e(k) function   
    true_avg = np.mean(x_kminus1)   

    # initializations for the while loop                                               
    x_k = np.zeros(len(all_nodes))
    transmissions = 0
    std_devs = []
    errors = []

    # while num_iterations < 25 or num_iterations > 20000 or not np.allclose(x_kminus1, true_avg):
    while (np.linalg.norm(x_k - np.ones(len(all_nodes)) * true_avg)**2 > TOL):
        x_k = np.dot(W, x_kminus1)                          # update the x vector
        std_devs.append((transmissions, np.std(x_k)))
        # e(k) = || . ||
        errors.append((transmissions, np.linalg.norm(x_k - np.ones(len(all_nodes)) * true_avg)**2))
        # x(k-1) = x(k)
        x_kminus1 = x_k

        # TRANSMISSIONS: for each iteration, transmissions increase by the number of edges in the graph
        transmissions += num_edges

    asym_conv_factor = np.max(np.linalg.eigvals(W - np.ones((len(all_nodes), len(all_nodes))) / len(all_nodes)))
    # print("Asymptotic convergence factor", asym_conv_factor)
    
    if np.max(np.mean(x_kminus1 - true_avg)) > TOL:
        print(f"\033[91mERROR: Not all values in x_k are within {TOL} of each other.\033[0m")
    
    end_time = time.time()
    execution_time = end_time - start_time
    print("Execution time:", execution_time, "seconds")
    print("Transmissions: ", transmissions)
    print("Average: ", x_kminus1[0])
    return x_kminus1[0], std_devs, errors, transmissions

'''
ASYNCH DIST AVG
1) x(k-1) = x(0)
2) while e(k) > epsilon:
    uniformly select random node i
    find all neighbors of node i
    Two methods to average:
        ''manual averaging of i and neighbor i values''
            x(k) = avg(x_i U x_ni)
        ''using the W matrix'' -- USED HERE
            construct W matrix
            check that W matrix obeys rules
            x(k) = W(k)x(k-1)
            x(k-1) = x(k)
    e(k) = || . ||
TRANSMISSIONS: per iteration of while loop = N(i)
'''
def dist_avg_asynch_W(graph, TOL):
    print("")
    print("------- ASYNCH. DIST. AVG. (W)------- ")
    start_time = time.time()

    # x(k-1) = x(0)
    x_kminus1 = np.array(list(nx.get_node_attributes(graph, "temp").values())) 

    # setup for e(k)
    true_avg = np.mean(x_kminus1)

    # initializations for the while loop
    all_nodes = list(nx.nodes(graph))  
    x_k = np.zeros(len(all_nodes))
    transmissions = 0 
    std_devs = []
    errors = []

    # while e(k) > epsilon:
    while (np.linalg.norm(x_k - np.ones(len(all_nodes)) * true_avg)**2 > TOL):
        # uniformly select random node i
        random_node_i = random.choice(all_nodes)

        # Construct the W matrix according to the current node selected
        # find all neighbors of node i
        list_neighbors_cur = list(nx.all_neighbors(graph, random_node_i))
        list_neighbors_cur.append(random_node_i)

        # Calculate the W matrix for node i
        W = np.zeros((len(all_nodes), len(all_nodes))) 

        for l in list_neighbors_cur:
            for m in list_neighbors_cur:
                W[l, m] = 1 / (graph.degree(random_node_i) + 1)
        
        for l in range(len(all_nodes)):
            for m in range(len(all_nodes)):
                if l == m and l not in list_neighbors_cur:
                    W[l, m] = 1
        
        # Check if W is symmetric
        if not np.allclose(W, W.T):
            print("\033[91mERROR: W is not symmetric.\033[0m")
            break
        
        # Check if W is doubly stochastic
        row_sums = np.sum(W, axis=1)
        col_sums = np.sum(W, axis=0)
        if not np.allclose(row_sums, 1) or not np.allclose(col_sums, 1):
            print("\033[91mERROR: W is not doubly stochastic.\033[0m")
            break

        # Check if W is nonnegative
        if not np.all(W >= 0):
            print("\033[91mERROR: W is not nonnegative.\033[0m")
            break

        # Check if abs(eigenvalues(W)) <= 1 + TOL (must do tolerance to account for overflow)
        eigenvalues = np.linalg.eigvals(W)
        if not np.all(np.abs(eigenvalues) <= 1.0 + TOL):
            print("\033[91mERROR: Absolute value of eigenvalues of W is not less than or equal to 1.\033[0m")
            break
        
        # x(k) = W(k)x(k-1)
        x_k = np.dot(W, x_kminus1)
        std_devs.append((transmissions, np.std(x_k)))
        errors.append((transmissions, np.linalg.norm(x_k - np.ones(len(all_nodes)) * true_avg)**2))
        x_kminus1 = x_k

        # TRANSMISSIONS: per iteration of while loop = N(i)
        transmissions += len(list_neighbors_cur)

    if np.max(np.mean(x_kminus1 - true_avg)) > TOL:
        print(f"\033[91mERROR: Not all values in x_k are within {TOL} of each other.\033[0m")
    
    end_time = time.time()
    execution_time = end_time - start_time
    print("Execution time:", execution_time, "seconds")
    print("Transmissions: ", transmissions)
    print("Average: ", x_kminus1[0])

    return x_kminus1[0], std_devs, errors, transmissions

'''
ASYNCH DIST AVG
1) x(k-1) = x(0)
2) while e(k) > epsilon:
    uniformly select random node i
    find all neighbors of node i
    Two methods to average:
        ''manual averaging of i and neighbor i values'' -- USED HERE
            x(k) = avg(x_i U x_ni)
            e(k) = || . ||
        ''using the W matrix'' 
            construct W matrix
            check that W matrix obeys rules
            x(k) = W(k)x(k-1)
            e(k) = || . ||
            x(k-1) = x(k)
TRANSMISSIONS: per iteration of while loop = N(i)
'''
def dist_avg_asynch_noW(graph, TOL):
    print("")
    print("------- ASYNCH. DIST. AVG. (no W)------- ")

    start_time = time.time()

    # x(k-1) = x(0)
    all_temps = nx.get_node_attributes(graph, "temp")
    
    # get true average, used for stopping criterion
    true_avg = np.mean(list(all_temps.values()))
    std_devs = []
    errors = []
    transmissions = 0

    all_nodes = list(nx.nodes(graph))
    while (np.linalg.norm(list(all_temps.values()) - np.ones(len(all_nodes)) * true_avg)**2 > TOL):
        # uniformly select random node i
        node_i = random.choice(all_nodes)
        
        # find all neighbors of node i
        neighbors_i = list(nx.all_neighbors(graph, node_i))

        # before computing the average, get values in set N(i) U i
        cur_temps = [all_temps[node] for node in neighbors_i]
        cur_temps.append(all_temps[node_i])

        avg = sum(cur_temps) / len(cur_temps)

        # update all nodes in set N(i) U i
        for node in neighbors_i:
            all_temps[node] = avg
        all_temps[node_i] = avg

        # TRANSMISSIONS: per iteration of while loop = N(i)
        transmissions += len(neighbors_i)

        # update values for plotting later
        std_dev = statistics.stdev(list(all_temps.values()))
        std_devs.append((transmissions, std_dev))

        # e(k) = || . ||
        errors.append((transmissions, np.linalg.norm(list(all_temps.values()) - np.ones(len(all_nodes)) * true_avg)**2))

    if np.max(np.mean(list(all_temps.values())) - true_avg) > TOL:
        print(f"\033[91mERROR: On average the values in x_k are not within {TOL} of each other.\033[0m")
    
    end_time = time.time()
    execution_time = end_time - start_time
    print("Execution time:", execution_time, "seconds")
    print("Transmissions: ", transmissions)
    print("Average: ", all_temps[0])

    return all_temps[0], std_devs, errors, transmissions

'''
RANDOMIZED GOSSIP
1) x(k-1) = x(0)
2) while e(k) > epsilon:
    uniformly select random node i
    uniformly select a neighbor of node i
    Two methods to average:
        ''manual averaging of i and neighbor i values'' -- USED HERE
            x(k) = avg(x_i, one_rand_neighbor)
            e(k) = || . ||
        ''using the W matrix'' 
            construct W matrix
            check that W matrix obeys rules
            x(k) = W(k)x(k-1)
            e(k) = || . ||
            x(k-1) = x(k)
TRANSMISSIONS: per iteration of while loop = 1
* decided to only implement the without W implementation because matrix multiplications implodes the time
'''
def random_gossip_noW(graph, TOL):
    print("")
    print("------- RANDOM GOSSIP (no W)------- ")

    start_time = time.time()

    # x(k-1) = x(0)
    all_temps = nx.get_node_attributes(graph, "temp")
    
    # get true average, used for stopping criterion
    true_avg = np.mean(list(all_temps.values()))
    std_devs = []
    errors = []
    transmissions = 0

    all_nodes = list(nx.nodes(graph))
    while (np.linalg.norm(list(all_temps.values()) - np.ones(len(all_nodes)) * true_avg)**2 > TOL):
        # uniformly select random node i
        node_i = random.choice(all_nodes)
        
        # uniformly select a neighbor of node i      
        neighbors_i = list(nx.all_neighbors(graph, node_i))
        rand_neigh = random.choice(neighbors_i) 

        # x(k) = avg(x_i, one_rand_neighbor)
        cur_temp = all_temps[node_i]
        neigh_temp = all_temps[rand_neigh]
        avg = (cur_temp + neigh_temp)/2
        all_temps.update({node_i: avg, rand_neigh: avg})

        # TRANSMISSIONS: per iteration of while loop = 1
        transmissions += 1

        # update values for plotting later
        std_dev = statistics.stdev(list(all_temps.values()))
        std_devs.append((transmissions, std_dev))

        # e(k) = || . ||
        errors.append((transmissions, np.linalg.norm(list(all_temps.values()) - np.ones(len(all_nodes)) * true_avg)**2))

    if np.max(np.mean(list(all_temps.values())) - true_avg) > TOL:
        print(f"\033[91mERROR: On average the values in x_k are not within {TOL} of each other.\033[0m")
    
    end_time = time.time()
    execution_time = end_time - start_time
    print("Execution time:", execution_time, "seconds")
    print("Transmissions: ", transmissions)
    print("Average: ", all_temps[0])

    return all_temps[0], std_devs, errors, transmissions
