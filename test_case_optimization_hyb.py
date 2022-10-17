# Copyright 2021 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import itertools
import click
import pandas as pd
from dwave.system import LeapHybridCQMSampler
from dimod import ConstrainedQuadraticModel, BinaryQuadraticModel, QuadraticModel

def parse_inputs(data_file):
    """Parse user input and files for data to build CQM.

    Args:
        data_file (csv file):
            File of items (weight & cost) slated to ship.
        capacity (int):
            Max weight the shipping container can accept.

    Returns:
        Costs, weights, and capacity.
    """
    df = pd.read_csv(data_file, names=['time', 'result'])

    # if not capacity:
    #     capacity = int(0.8 * sum(df['weight']))
    #     print("\nSetting weight capacity to 80% of total: {}".format(str(capacity)))

    return df['time'], df['result']

def build_testcase_bqm(time, result):
    """Construct a BQM for tnapsack problem.

    Args:
        time (array-like):
            Array of time costs for test cases
        result (array-like):
            Array of failing rates for test cases


    Returns:
        Constrained quadratic model instance that represents the knapsack problem.
    """
    num_items = len(time)
    print("\nBuilding a BQM for {} items.".format(str(num_items)))

    cqm = ConstrainedQuadraticModel()
    obj = BinaryQuadraticModel(vartype='BINARY')
    constraint1 = QuadraticModel()

    time_total = sum(time)
    result_total = sum(result)
    cofficient = []
    for i in range(num_items):
        cofficient.append((1/3)*time[i]/time_total - (1/3)*result[i]/result_total + (1/3)*1/num_items)
        print('time: '+str(time[i]/time_total))
        print('result: '+str(result[i]/result_total))
        print('num: '+str(1/num_items))
    print(time_total)
    print(num_items)
    print(result_total)
    print(cofficient)

    for i in range(num_items):
        # Objective is to maximize the total costs
        obj.add_variable(i)
        obj.set_linear(i, cofficient[i])
        # Constraint is to keep the sum of items' weights under or equal capacity
        constraint1.add_variable('BINARY', i)
        constraint1.set_linear(i, result[i])
        #constraint2.add_variable('BINARY', i)
        #constraint2.set_linear(i, time[i])

    cqm.set_objective(obj)
    cqm.add_constraint(constraint1, sense=">=", rhs=1, label='result')
    #cqm.add_constraint(constraint2, sense='<=',rhs=150,label='time')
    
    return cqm

def parse_solution(sampleset, time, result):
    """Translate the best sample returned from solver to shipped items.

    Args:

        sampleset (dimod.Sampleset):
            Samples returned from the solver.
        time (array-like):
            Array of time costs for the test cases.
        failing rates (array-like):
            Array of failing rates for the test cases.
    """
    feasible_sampleset = sampleset.filter(lambda row: row.is_feasible)

    if not len(feasible_sampleset):
        raise ValueError("No feasible solution found")

    best = feasible_sampleset.first

    selected_item_indices = [key for key, val in best.sample.items() if val==1.0]
    selected_time  = list(time.loc[selected_item_indices])
    selected_result = list(result.loc[selected_item_indices])

    # selected_weights = list(weights.loc[selected_item_indices])
    # selected_costs = list(costs.loc[selected_item_indices])

    print("\nFound best solution at energy {}".format(best.energy))
    print("\nSelected item numbers (0-indexed):", selected_item_indices)
    print("\nSelected item time: {}, total = {}".format(selected_time, sum(selected_result)))
    print("\nSelected item failure rate: {}, total = {}".format(selected_result, sum(selected_result)))
    # print("\nSelected item costs: {}, total = {}".format(selected_costs, sum(selected_costs)))

def datafile_help(max_files=5):
    """Provide content of input file names for click()'s --help."""

    try:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        datafiles = os.listdir(data_dir)
        # "\b" enables newlines in click() help text
        help = """
\b
Name of data file (under the 'data/' folder) to run on.
One of:
File Name \t Total weight
"""
        for file in datafiles[:max_files]:
            _, weights, _ = parse_inputs(os.path.join(data_dir, file))
            help += "{:<20} {:<10} \n".format(str(file), str(sum(weights)))
        help += "\nDefault is to run on data/large.csv."
    except:
        help = """
\b
Name of data file (under the 'data/' folder) to run on.
Default is to run on data/experiments.csv.
"""

    return help

filename_help = datafile_help()     # Format the help string for the --filename argument

@click.command()
@click.option('--filename', type=click.File(), default='data/large.csv',
              help=filename_help)

def main(filename):
    """Solve a test case optimization problem using a CQM solver."""

    sampler = LeapHybridCQMSampler()

    time, result = parse_inputs(filename)

    bqm = build_testcase_bqm(time, result)

    print("Submitting CQM to solver {}.".format(sampler.solver.name))

    sampleset = sampler.sample_cqm(bqm, label='example')

    # print(sampleset)

    #sampleset = sampler.sample_cqm(cqm, label='Example - Knapsack')

    parse_solution(sampleset, time, result)

if __name__ == '__main__':
    main()
