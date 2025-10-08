import math

def softmax(scores: list):
    if len(scores) == 0:
        return []

    max_score: float = max(scores)
    exp_scores: list = [math.exp(s - max_score) for s in scores]
    sum_exp: float = sum(exp_scores)

    return [e / sum_exp for e in exp_scores]

def bayesian_update(prior_vectors: dict, likelihood: dict, normalized: bool = False, alpha: float = 1.0) -> tuple[bool, dict]:
    
    # normalize all values for likelihood using softmax activation
    if not normalized:
        likelihood_values: list = list(likelihood.values())
        likelihood_values = softmax(likelihood_values)

        for i, (k, _) in enumerate(likelihood.items()):
            likelihood[k] = likelihood_values[i]
    
    # remove keys from prior if the are not considered as 
    # trip candidates in the current update anymore
    # also add new candidates to prior if they are in likelihood
    prior_vectors = {k: v for k, v in prior_vectors.items() if k in likelihood}

    for k, v in likelihood.items():
        if k not in prior_vectors:
            prior_vectors[k] = [v]

    # ensure that prior and likelihood are sorted both by their key 
    prior_vectors = dict(sorted(prior_vectors.items()))
    likelihood = dict(sorted(likelihood.items()))

    # extract all values
    likelihood_values: list = list(likelihood.values())
    prior_vectors_values: list = list(prior_vectors.values())

    # calulate update according to the bayesian rule
    unnormalized_posterior: list = [
        p[-1] * (l ** alpha) for p, l in zip(prior_vectors_values, likelihood_values)
    ]

    total_posterior: float = sum(unnormalized_posterior)

    # normalize posterior and re-create dict
    if total_posterior == 0.0:
        posterior: list = [0.0 for _ in unnormalized_posterior]
    else:
        posterior: list = [u / total_posterior for u in unnormalized_posterior]

    posterior_vectors: dict = prior_vectors
    for i, (k, _) in enumerate(prior_vectors.items()):
        posterior_vectors[k].append(posterior[i])

    # check best candidate for convergence
    convergence: bool = False

    convergence_key: str = max(posterior_vectors, key=lambda k: posterior_vectors[k][-1])
    convergence_vector: list[float] = posterior_vectors[convergence_key]
    convergence_test: float = convergence_vector[-1]

    if convergence_test > 0.98:
        convergence = True
    elif convergence_test > 0.50:
        convergence_vector = convergence_vector[-3:]

        deltas: list[float] = [abs(b - a) for a, b in zip(convergence_vector, convergence_vector[1:])]
        convergence = all(delta < 0.02 for delta in deltas)

    return (convergence, posterior_vectors)