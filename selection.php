<?php
// Simple UI to run ai/topstock/selection.py and show generated CSVs.

$stock = '';
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $stock = isset($_GET['id']) ? preg_replace('/[^0-9A-Za-z\.]/', '', $_GET['id']) : '';
    if ($stock !== '') {
        $cmd = 'python3 ./selection.py --print N --id ' . escapeshellarg($stock);
        $outputLines = [];
        $returnVar = 0;
        exec($cmd . ' 2>&1', $outputLines, $returnVar);

        $cmdOutput = implode("\n", $outputLines);

        //locations where selection CSVs may be written
        $csvFolder = "./selection";

        $foundFiles = [];
        if (!is_dir($csvFolder)) die('Error: ' . $csvFolder . ' folder not found.');
        $matches = glob($csvFolder . '/' . $stock . '_*.csv');
        if ($matches && count($matches) > 0) {
            foreach ($matches as $m) $foundFiles[] = $m;
        }
    }
}

function read_csv_rows($file) {
    $rows = [];
    if (!file_exists($file)) return $rows;
    if (($h = fopen($file, 'r')) !== false) {
        while (($data = fgetcsv($h)) !== false) {
            $rows[] = $data;
        }
        fclose($h);
    }
    return $rows;
}

?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Selection Runner</title>
    <style>
        table{border-collapse:collapse}
        td,th{border:1px solid #ccc;padding:6px}
        .toggle-btn{cursor:pointer;background:#f0f0f0;border:1px solid #ccc;padding:2px 6px;border-radius:3px;font-weight:bold}
        .toggle-btn:focus{outline:2px solid #88f}
    </style>
</head>
<body>
    <h2>Run Selection</h2>
    <form method="get">
        Stock code: <input name="id" value="<?php echo htmlspecialchars($stock); ?>"> 
        <button type="submit">Run</button>
    </form>

<?php if (!empty($cmdOutput) || isset($returnVar)): ?>
    <h3>Script Output (exit code <?php echo intval($returnVar); ?>)</h3>
    <pre><?php echo htmlspecialchars($cmdOutput); ?></pre>
<?php endif; ?>

<?php if (isset($foundFiles) && count($foundFiles) > 0): ?>
    <?php
    // Build a combined summary table: date, open, high, low, volume, amount,
    // and for each strategy: signal, position, hold_days
    $summary = [];
    $strategies = [];
    $total_strategies = count($foundFiles);
    foreach ($foundFiles as $file) {
        $bn = basename($file);
        $parts = explode('_', $bn);
        $strategy = count($parts) === 3 ? preg_replace('/\.csv$/i', '', $parts[2]) : preg_replace('/\.csv$/i', '', $bn);
        $strategies[] = $strategy;
        $rows = read_csv_rows($file);
        if (count($rows) < 2) continue;
        $header = $rows[0];
        $map = [];
        foreach ($header as $i => $h) $map[strtolower(trim($h))] = $i;
        for ($ri = 1; $ri < count($rows); $ri++) {
            $r = $rows[$ri];
            $date = null;
            if (isset($map['date']) && isset($r[$map['date']])) $date = $r[$map['date']];
            elseif (isset($r[0])) $date = $r[0];
            if ($date === null) continue;
            if (!isset($summary[$date])) $summary[$date] = ['date' => $date];
            foreach (['open','high','low','volume','amount'] as $c) {
                if (isset($map[$c]) && isset($r[$map[$c]])) $summary[$date][$c] = $r[$map[$c]];
            }
            $signal = null; $position = null; $hold = null;
            foreach ($map as $k => $idx) {
                if ($signal === null && strpos($k, 'signal') !== false && isset($r[$idx])) $signal = $r[$idx];
                if ($position === null && strpos($k, 'position') !== false && isset($r[$idx])) $position = $r[$idx];
                if ($hold === null && (strpos($k, 'hold') !== false || strpos($k, 'hold_days') !== false) && isset($r[$idx])) $hold = $r[$idx];
            }
            $summary[$date][$strategy . '_signal'] = $signal;
            $summary[$date][$strategy . '_position'] = $position;
            $summary[$date][$strategy . '_hold_days'] = $hold;

            // compute numeric position contribution for position summary
            if (!isset($summary[$date]['position_summary'])) $summary[$date]['position_summary'] = 0;
            $posNum = 0.0;
            if ($position !== null && $position !== '') {
                $clean = str_replace([',','%'], ['', ''], $position);
                // allow values like "1.23e3" etc; floatval will handle
                $posNum = floatval($clean);
            }
            // special handling for VolatilityControlStrategy
            if (strtolower($strategy) === strtolower('VolatilityControlStrategy')) {
                $posNum = $posNum / 2000.0;
            }
            // if $hold = 0, treat as no position
            if ($hold !== null && is_numeric($hold) && intval($hold) === 0) {
                $posNum = 0.0;
            }
            // keep one decimal place for each strategy contribution
            $posNum = round($posNum, 1);
            $summary[$date]['position_summary'] += $posNum;
        }
    }
    $strategies = array_values(array_unique($strategies));
    ksort($summary);
    ?>

    <h3>Summary Table</h3>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Open</th>
                <th>High</th>
                <th>Low</th>
                <th>Volume</th>
                <th>Amount</th>
                <th>Position Summary</th>
                <?php foreach ($strategies as $s): ?>
                    <th><?php echo htmlspecialchars($s); ?> signal</th>
                    <th><?php echo htmlspecialchars($s); ?> position</th>
                    <th><?php echo htmlspecialchars($s); ?> hold_days</th>
                <?php endforeach; ?>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($summary as $row): ?>
                <tr>
                    <td><?php echo htmlspecialchars($row['date']); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['open']) ? $row['open'] : ''); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['high']) ? $row['high'] : ''); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['low']) ? $row['low'] : ''); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['volume']) ? $row['volume'] : ''); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['amount']) ? $row['amount'] : ''); ?></td>
                    <td><?php echo htmlspecialchars(isset($row['position_summary']) ? $row['position_summary'] . ' / ' . $total_strategies : ''); ?></td>
                    <?php foreach ($strategies as $s): ?>
                        <?php
                            $hold = isset($row[$s . '_hold_days']) ? $row[$s . '_hold_days'] : '';
                            $is_red = false;
                            if ($hold !== '') {
                                $clean_hold = str_replace([',','%'], ['', ''], $hold);
                                if (is_numeric($clean_hold) && intval($clean_hold) > 0) $is_red = true;
                            }
                        ?>
                        <td<?php echo $is_red ? ' style="color:#FFA616"' : ''; ?>><?php echo htmlspecialchars(isset($row[$s . '_signal']) ? $row[$s . '_signal'] : ''); ?></td>
                        <td<?php echo $is_red ? ' style="color:#FFA616"' : ''; ?>><?php echo htmlspecialchars(isset($row[$s . '_position']) ? $row[$s . '_position'] : ''); ?></td>
                        <td<?php echo $is_red ? ' style="color:#FFA616"' : ''; ?>><?php echo htmlspecialchars($hold); ?></td>
                    <?php endforeach; ?>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <h3>Generated CSVs</h3>
    <?php foreach ($foundFiles as $file): ?>
        <?php $rows = read_csv_rows($file); ?>
        <h4><?php echo htmlspecialchars(basename($file)); ?></h4>
        <?php if (count($rows) > 0): ?>
            <table>
                <thead>
                    <tr>
                    <?php foreach ($rows[0] as $h): ?>
                        <th><?php echo htmlspecialchars($h); ?></th>
                    <?php endforeach; ?>
                    </tr>
                </thead>
                <tbody>
                <?php for ($i = 1; $i < count($rows); $i++): ?>
                    <tr>
                    <?php foreach ($rows[$i] as $c): ?>
                        <td><?php echo htmlspecialchars($c); ?></td>
                    <?php endforeach; ?>
                    </tr>
                <?php endfor; ?>
                </tbody>
            </table>
        <?php else: ?>
            <p>No rows in file.</p>
        <?php endif; ?>
    <?php endforeach; ?>
<?php elseif ($_SERVER['REQUEST_METHOD'] === 'GET'): ?>
    <p>No CSVs found for <?php echo htmlspecialchars($stock); ?>. Check script output above.</p>
<?php endif; ?>

</body>
<script>
document.addEventListener('DOMContentLoaded', function(){
    const h3s = Array.from(document.querySelectorAll('h3'));
    h3s.forEach(function(h3){
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'toggle-btn';
        btn.setAttribute('aria-expanded','false');
        btn.textContent = '+';
        if (h3.firstChild) h3.insertBefore(btn, h3.firstChild);
        else h3.appendChild(btn);

        // gather siblings until next H3
        let sib = h3.nextElementSibling;
        const group = [];
        while(sib && sib.tagName !== 'H3'){
            group.push(sib);
            sib = sib.nextElementSibling;
        }
        // hide them by default (but keep Summary Table expanded)
        const headingText = h3.textContent.replace(/^\s*[+−]\s*/, '').trim();
        const isSummary = /summary table/i.test(headingText);
        group.forEach(el => el.style.display = isSummary ? '' : 'none');
        if (isSummary) {
            btn.setAttribute('aria-expanded','true');
            btn.textContent = '−';
        }

        btn.addEventListener('click', function(){
            const expanded = btn.getAttribute('aria-expanded') === 'true';
            group.forEach(el => el.style.display = expanded ? 'none' : '');
            btn.setAttribute('aria-expanded', (!expanded).toString());
            btn.textContent = expanded ? '+' : '−';
        });
    });
});
</script>
</html>
