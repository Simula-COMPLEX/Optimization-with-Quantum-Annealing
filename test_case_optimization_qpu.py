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
from dimod import BinaryQuadraticModel
import dimod
from dwave.system import DWaveSampler, EmbeddingComposite

def parse_inputs(data_file):
    """Parse user input and files for data to build CQM.

    Args:
        data_file (csv file):
            File of test case time and failure rate.

    Returns:
        Time and failure rate
    """
    df = pd.read_csv(data_file, names=['time', 'result'])

    # if not capacity:
    #     capacity = int(0.8 * sum(df['weight']))
    #     print("\nSetting weight capacity to 80% of total: {}".format(str(capacity)))

    return df['time'], df['result']

def build_testcase_bqm(time, result):
    """Construct a BQM for test case optimization problem.

    Args:
        time (array-like):
            Array of costs for the items.
        pass (array-like):
            Array of weights for the items.
        max_weight (int):
            Maximum allowable weight for the knapsack.

    Returns:
        Constrained quadratic model instance that represents the knapsack problem.
    """
    num_items = len(time)
    print("\nBuilding a CQM for {} items.".format(str(num_items)))

    # bqm = ConstrainedQuadraticModel()
    # obj = BinaryQuadraticModel(vartype='BINARY')
    # constraint1 = QuadraticModel()

    time_total = sum(time)
    result_total = sum(result)
    cofficient = []
    for i in range(num_items):
        cofficient.append((1/3)*time[i]/time_total - (1/3)*result[i]/result_total + (1/3)*1/num_items)

    dic = {}
    for i in range(len(cofficient)):
        dic[i] = cofficient[i]

    print(dic)

    bqm = BinaryQuadraticModel(dic, {}, 0, dimod.Vartype.BINARY)

    
    return bqm

def parse_solution(sampleset, time, result):
    """Translate the best sample returned from solver to test cases.

    Args:

        sampleset (dimod.Sampleset):
            Samples returned from the solver.
        time (array-like):
            Array of time for the test cases.
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
    """Provide content of input file names and total weights for click()'s --help."""

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
Default is to run on data/large.csv.
"""

    return help

filename_help = datafile_help()     # Format the help string for the --filename argument

@click.command()
@click.option('--filename', type=click.File(), default='data/experiments.csv',
              help=filename_help)
# @click.option('--capacity', default=None,
#               help="Maximum weight for the container. By default sets to 80% of the total.")
def main(filename):
    """Solve a test case optimization problem using a CQM solver."""

    sampler = EmbeddingComposite(DWaveSampler(solver={'qpu':True}))

    time, result = parse_inputs(filename)

    bqm = build_testcase_bqm(time, result)

    sampleset = sampler.sample(bqm, num_reads=1000)
    
    print(sampleset)

    print(sampleset.first)

    print(sampleset.lowest())

    print(sampleset.info['timing'])

if __name__ == '__main__':
    main()
