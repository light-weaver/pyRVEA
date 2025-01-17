import numpy as np
from warnings import warn
from typing import List
from desdeo_emo.selection.SelectionBase import SelectionBase
from desdeo_emo.population.Population import Population
from desdeo_emo.othertools.ReferenceVectors import ReferenceVectors


class APD_Select(SelectionBase):
    """The selection operator for the RVEA algorithm. Read the following paper for more
        details.
        R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, A Reference Vector Guided
        Evolutionary Algorithm for Many-objective Optimization, IEEE Transactions on
        Evolutionary Computation, 2016
    Parameters
    ----------
    pop : Population
        The population instance
    iteration_length : int
        Length of the iteration
    alpha : float, optional
        The RVEA alpha parameter, by default 2
    """

    def __init__(self, pop: Population, iteration_length: int, alpha: float = 2):
        self.iteration_length = iteration_length
        self.gen_counter = 1
        self.alpha = 2
        self.n_of_objectives = pop.problem.n_of_objectives

    def do(self, pop: Population, vectors: ReferenceVectors) -> List[int]:
        """Select individuals for mating on basis of Angle penalized distance.

        Parameters
        ----------
        pop : Population
            The current population.
        vectors : ReferenceVectors
            Class instance containing reference vectors.

        Returns
        -------
        List[int]
            List of indices of the selected individuals
        """
        partial_penalty_factor = self._partial_penalty_factor()
        refV = vectors.neighbouring_angles_current
        # Normalization - There may be problems here
        if pop.ideal_fitness_val is not None:
            fmin = pop.ideal_fitness_val
        else:
            fmin = np.amin(pop.fitness, axis=0)
        translated_fitness = pop.fitness - fmin
        fitness_norm = np.linalg.norm(translated_fitness, axis=1)
        # TODO check if you need the next line
        fitness_norm = np.repeat(fitness_norm, len(translated_fitness[0, :])).reshape(
            len(pop.fitness), len(pop.fitness[0, :])
        )
        # Convert zeros to eps to avoid divide by zero.
        # Has to be checked!
        fitness_norm[fitness_norm == 0] = np.finfo(float).eps
        normalized_fitness = np.divide(
            translated_fitness, fitness_norm
        )  # Checked, works.
        cosine = np.dot(normalized_fitness, np.transpose(vectors.values))
        if cosine[np.where(cosine > 1)].size:
            warn("RVEA.py line 60 cosine larger than 1 decreased to 1")
            cosine[np.where(cosine > 1)] = 1
        if cosine[np.where(cosine < 0)].size:
            warn("RVEA.py line 64 cosine smaller than 0 increased to 0")
            cosine[np.where(cosine < 0)] = 0
        # Calculation of angles between reference vectors and solutions
        theta = np.arccos(cosine)
        # Reference vector asub_population_indexssignment
        assigned_vectors = np.argmax(cosine, axis=1)
        selection = np.array([], dtype=int)
        # Selection
        # Convert zeros to eps to avoid divide by zero.
        # Has to be checked!
        refV[refV == 0] = np.finfo(float).eps
        for i in range(0, len(vectors.values)):
            sub_population_index = np.atleast_1d(
                np.squeeze(np.where(assigned_vectors == i))
            )
            sub_population_fitness = translated_fitness[sub_population_index]
            if len(sub_population_fitness > 0):
                # APD Calculation
                angles = theta[sub_population_index, i]
                angles = np.divide(angles, refV[i])  # This is correct.
                # You have done this calculation before. Check with fitness_norm
                # Remove this horrible line
                sub_pop_fitness_magnitude = np.sqrt(
                    np.sum(np.power(sub_population_fitness, 2), axis=1)
                )
                apd = np.multiply(
                    np.transpose(sub_pop_fitness_magnitude),
                    (1 + np.dot(partial_penalty_factor, angles)),
                )
                minidx = np.where(apd == np.nanmin(apd))
                if np.isnan(apd).all():
                    continue
                selx = sub_population_index[minidx]
                if selection.shape[0] == 0:
                    selection = np.hstack((selection, np.transpose(selx[0])))
                else:
                    selection = np.vstack((selection, np.transpose(selx[0])))
        return selection.squeeze()

    def _partial_penalty_factor(self) -> float:
        """Calculate and return the partial penalty factor for APD calculation.
            This calculation does not include the angle related terms, hence the name.

        Returns
        -------
        float
            The partial penalty value
        """
        penalty = (
            (self.gen_counter / self.iteration_length) ** self.alpha
        ) * self.n_of_objectives
        return penalty
