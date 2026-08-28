from pathlib import Path


def write_element_mass(
    nodal_masses,
    output_path,
    start_eid,
    zero_tolerance=0.0,
):
    """
    NODEごとの追加質量を *ELEMENT_MASS としてKファイルへ出力する。

    Parameters
    ----------
    nodal_masses : dict
        NODE IDをキー、質量を値とする辞書

        例:
        {
            1: 0.00123,
            2: 0.00456,
            3: 0.0,
        }

    output_path : str or Path
        出力するKファイルのパス

    start_eid : int
        *ELEMENT_MASS に使用する開始ELEMENT ID

    zero_tolerance : float, optional
        この値以下の質量は出力しない。
        デフォルトは0.0

    Returns
    -------
    dict
        出力結果

        {
            "written_count": ...,
            "skipped_count": ...,
            "first_eid": ...,
            "last_eid": ...
        }
    """

    output_path = Path(output_path)

    # 出力先フォルダがなければ作成
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    eid = start_eid

    written_count = 0
    skipped_count = 0

    first_eid = None
    last_eid = None

    with output_path.open(
        mode="w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        # -------------------------
        # Header
        # -------------------------

        f.write("*KEYWORD\n")
        f.write("*ELEMENT_MASS\n")
        f.write(
            "$      EID     NID            MASS\n"
        )

        # -------------------------
        # ELEMENT_MASS
        # -------------------------

        for nid in sorted(nodal_masses):

            mass = nodal_masses[nid]

            # 0または非常に小さい質量は省略
            if mass <= zero_tolerance:
                skipped_count += 1
                continue

            if first_eid is None:
                first_eid = eid

            # EID : 8桁
            # NID : 8桁
            # MASS: 16桁
            line = (
                f"{eid:8d}"
                f"{nid:8d}"
                f"{mass:16.8E}\n"
            )

            f.write(line)

            last_eid = eid

            eid += 1
            written_count += 1

        # -------------------------
        # End
        # -------------------------

        f.write("*END\n")

    return {
        "written_count": written_count,
        "skipped_count": skipped_count,
        "first_eid": first_eid,
        "last_eid": last_eid,
    }


