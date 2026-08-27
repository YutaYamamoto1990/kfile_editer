import numpy as np

from scipy.optimize import differential_evolution


def prepare_node_arrays(target_nodes):
    """
    対象NODE辞書をNumPy配列へ変換する。

    Parameters
    ----------
    target_nodes : dict
        {
            nid: {
                "x": ...,
                "y": ...,
                "z": ...
            }
        }

    Returns
    -------
    node_ids : np.ndarray
    x : np.ndarray
    z : np.ndarray
    """

    node_ids = np.fromiter(
        target_nodes.keys(),
        dtype=np.int64,
        count=len(target_nodes),
    )

    x = np.fromiter(
        (node["x"] for node in target_nodes.values()),
        dtype=float,
        count=len(target_nodes),
    )

    z = np.fromiter(
        (node["z"] for node in target_nodes.values()),
        dtype=float,
        count=len(target_nodes),
    )

    return node_ids, x, z


def normalize_xz(x, z):
    """
    X-Z座標を中心化・スケーリングする。

    XとZの寸法差によって探索方向thetaの意味が
    歪まないようにする。

    Returns
    -------
    x_norm : np.ndarray
    z_norm : np.ndarray
    info : dict
    """

    x_center = np.mean(x)
    z_center = np.mean(z)

    x_range = np.max(x) - np.min(x)
    z_range = np.max(z) - np.min(z)

    if x_range == 0.0:
        raise ValueError("X方向のNODE範囲が0です。")

    if z_range == 0.0:
        raise ValueError("Z方向のNODE範囲が0です。")

    x_norm = (x - x_center) / x_range
    z_norm = (z - z_center) / z_range

    info = {
        "x_center": x_center,
        "z_center": z_center,
        "x_range": x_range,
        "z_range": z_range,
    }

    return x_norm, z_norm, info


def calculate_ramp_weights(
    x_norm,
    z_norm,
    theta,
    d,
):
    """
    2次元ランプによる相対重みを計算する。

    w_i = max(
        0,
        cos(theta) * x_i
        + sin(theta) * z_i
        - d
    )

    Parameters
    ----------
    theta : float
        ランプ方向 [rad]

    d : float
        ランプ立ち上がり位置

    Returns
    -------
    np.ndarray
        各NODEの相対重み
    """

    projection = (
        np.cos(theta) * x_norm
        + np.sin(theta) * z_norm
    )

    weights = np.maximum(
        0.0,
        projection - d,
    )

    return weights


def calculate_weighted_cg(
    weights,
    x,
    z,
):
    """
    相対重みから重心を計算する。
    """

    weight_sum = np.sum(weights)

    if weight_sum <= 0.0:
        return None

    cg_x = np.sum(weights * x) / weight_sum
    cg_z = np.sum(weights * z) / weight_sum

    return cg_x, cg_z


def calculate_normalized_cg_error(
    cg_x,
    cg_z,
    target_cg_x,
    target_cg_z,
    x_range,
    z_range,
):
    """
    X,Zの寸法差を考慮した正規化重心誤差。
    """

    dx = (
        cg_x - target_cg_x
    ) / x_range

    dz = (
        cg_z - target_cg_z
    ) / z_range

    return np.sqrt(
        dx * dx + dz * dz
    )


def optimize_ramp_distribution(
    target_nodes,
    total_mass,
    target_cg_x,
    target_cg_z,
    cg_tolerance=1.0e-4,
    theta_bounds=(0.0, 2.0 * np.pi),
    d_bounds=(-2.0, 1.0),
):
    """
    2次元ランプ質量分布を最適化する。

    Lexicographic optimization:

    第1目的:
        重心誤差をcg_tolerance以内にする

    第2目的:
        条件を満たす範囲でdを最小化する

    条件を満たせない場合:
        重心誤差が最小の解を採用する

    Parameters
    ----------
    target_nodes : dict
        対象NODE辞書

    total_mass : float
        追加総質量

    target_cg_x : float
        目標重心X

    target_cg_z : float
        目標重心Z

    cg_tolerance : float
        正規化重心誤差の許容値

    theta_bounds : tuple
        theta探索範囲 [rad]

    d_bounds : tuple
        d探索範囲

    Returns
    -------
    dict
        最適化結果
    """

    if total_mass <= 0.0:
        raise ValueError(
            "total_massは正の値を指定してください。"
        )

    if not target_nodes:
        raise ValueError(
            "対象NODEがありません。"
        )

    # ---------------------------------
    # NODEデータをNumPy配列化
    # ---------------------------------

    node_ids, x, z = prepare_node_arrays(
        target_nodes
    )

    x_norm, z_norm, norm_info = normalize_xz(
        x,
        z,
    )

    x_range = norm_info["x_range"]
    z_range = norm_info["z_range"]

    # ---------------------------------
    # まずCG誤差だけを最小化
    # ---------------------------------

    def cg_objective(params):

        theta, d = params

        weights = calculate_ramp_weights(
            x_norm,
            z_norm,
            theta,
            d,
        )

        cg = calculate_weighted_cg(
            weights,
            x,
            z,
        )

        if cg is None:
            return 1.0e6

        cg_x, cg_z = cg

        return calculate_normalized_cg_error(
            cg_x,
            cg_z,
            target_cg_x,
            target_cg_z,
            x_range,
            z_range,
        )

    bounds = [
        theta_bounds,
        d_bounds,
    ]

    cg_result = differential_evolution(
        cg_objective,
        bounds=bounds,
        polish=True,
    )

    best_theta = cg_result.x[0]
    best_d = cg_result.x[1]
    best_cg_error = cg_result.fun

    # ---------------------------------
    # CG条件を満たせる場合
    # dをできるだけ小さくする
    # ---------------------------------

    cg_condition_met = (
        best_cg_error <= cg_tolerance
    )

    if cg_condition_met:

        # CG誤差を超える場合は大きな罰則を与える。
        # 許容範囲内ならdだけを評価する。

        penalty_scale = 1.0e6

        def lexicographic_objective(params):

            theta, d = params

            weights = calculate_ramp_weights(
                x_norm,
                z_norm,
                theta,
                d,
            )

            cg = calculate_weighted_cg(
                weights,
                x,
                z,
            )

            if cg is None:
                return 1.0e12

            cg_x, cg_z = cg

            cg_error = calculate_normalized_cg_error(
                cg_x,
                cg_z,
                target_cg_x,
                target_cg_z,
                x_range,
                z_range,
            )

            if cg_error <= cg_tolerance:
                return d

            excess = (
                cg_error - cg_tolerance
            )

            return (
                d
                + penalty_scale * excess
            )

        lex_result = differential_evolution(
            lexicographic_objective,
            bounds=bounds,
            polish=True,
        )

        best_theta = lex_result.x[0]
        best_d = lex_result.x[1]

    # ---------------------------------
    # 最終ランプ
    # ---------------------------------

    weights = calculate_ramp_weights(
        x_norm,
        z_norm,
        best_theta,
        best_d,
    )

    weight_sum = np.sum(weights)

    if weight_sum <= 0.0:
        raise RuntimeError(
            "最適化後のランプ重みがすべて0です。"
        )

    # ---------------------------------
    # 総質量で正規化
    # ---------------------------------

    masses = (
        total_mass
        * weights
        / weight_sum
    )

    # ---------------------------------
    # 最終CG
    # ---------------------------------

    total_mass_actual = np.sum(masses)

    cg_x = (
        np.sum(masses * x)
        / total_mass_actual
    )

    cg_z = (
        np.sum(masses * z)
        / total_mass_actual
    )

    cg_error = calculate_normalized_cg_error(
        cg_x,
        cg_z,
        target_cg_x,
        target_cg_z,
        x_range,
        z_range,
    )

    # ---------------------------------
    # NODE ID -> mass
    # ---------------------------------

    nodal_masses = {
        int(nid): float(mass)
        for nid, mass in zip(
            node_ids,
            masses,
        )
    }

    positive_count = int(
        np.count_nonzero(
            masses > 0.0
        )
    )

    zero_count = int(
        len(masses) - positive_count
    )

    return {
        "nodal_masses": nodal_masses,

        "theta": float(best_theta),
        "theta_deg": float(
            np.degrees(best_theta)
        ),

        "d": float(best_d),

        "total_mass": float(
            total_mass_actual
        ),

        "target_cg_x": float(
            target_cg_x
        ),

        "target_cg_z": float(
            target_cg_z
        ),

        "cg_x": float(cg_x),
        "cg_z": float(cg_z),

        "cg_error": float(cg_error),

        "cg_tolerance": float(
            cg_tolerance
        ),

        "cg_condition_met": (
            cg_error <= cg_tolerance
        ),

        "min_mass": float(
            np.min(masses)
        ),

        "max_mass": float(
            np.max(masses)
        ),

        "positive_node_count": (
            positive_count
        ),

        "zero_mass_node_count": (
            zero_count
        ),

        "total_node_count": int(
            len(masses)
        ),

        "normalization": norm_info,

        "x_min": float(np.min(x)),
        "x_max": float(np.max(x)),
        "z_min": float(np.min(z)),
        "z_max": float(np.max(z)),

        "cg_error_x": float(
            cg_x - target_cg_x
        ),

        "cg_error_z": float(
            cg_z - target_cg_z
        ),
    }


