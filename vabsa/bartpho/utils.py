{"metadata":{"kernelspec":{"language":"python","display_name":"Python 3","name":"python3"},"language_info":{"name":"python","version":"3.10.10","mimetype":"text/x-python","codemirror_mode":{"name":"ipython","version":3},"pygments_lexer":"ipython3","nbconvert_exporter":"python","file_extension":".py"}},"nbformat_minor":4,"nbformat":4,"cells":[{"cell_type":"code","source":"import torch\nimport numpy as np\nfrom preprocess import tokenize, normalize\ntag_dict = {\n    \"RESTAURANT#GENERAL\": \"chung về nhà_hàng\",\n    \"RESTAURANT#PRICES\": \"giá của nhà_hàng\",\n    \"RESTAURANT#MISCELLANEOUS\": \"tổng_quát về nhà_hàng\",\n    \"FOOD#PRICES\": \"giá đồ ăn\",\n    \"FOOD#QUALITY\": \"chất_lượng đồ ăn\",\n    \"FOOD#STYLE&OPTIONS\": \"phong_cách và lựa_chọn đồ ăn\",\n    \"DRINKS#PRICES\": \"giá đồ uống\",\n    \"DRINKS#QUALITY\": \"chất_lượng đồ uống\",\n    \"DRINKS#STYLE&OPTIONS\": \"phong_cách và lựa_chọn đồ uống\",\n    \"AMBIENCE#GENERAL\": \"bầu không_khí\",\n    \"SERVICE#GENERAL\": \"dịch_vụ\",\n    \"LOCATION#GENERAL\": \"vị_trí\",\n}\n\npolarity_dict = {\n    \"không có\": \"không có\",\n    \"positive\": \"tích_cực\",\n    \"neutral\": \"trung_lập\",\n    \"negative\": \"tiêu_cực\"\n}\n\npolarity_list = [\"không có\", \"tích_cực\", \"trung_lập\", \"tiêu_cực\"]\ntags = [\"chung về nhà_hàng\",\"giá của nhà_hàng\",\"tổng_quát về nhà_hàng\",\"giá đồ ăn\",\n        \"chất_lượng đồ ăn\",\"phong_cách và lựa_chọn đồ ăn\",\"giá đồ uống\",\"chất_lượng đồ uống\",\n        \"phong_cách và lựa_chọn đồ uống\",\"bầu không_khí\",\"dịch_vụ\",\"vị_trí\"]\neng_tags = [\"RESTAURANT#GENERAL\",\"RESTAURANT#PRICES\",\"RESTAURANT#MISCELLANEOUS\",\"FOOD#PRICES\",\n            \"FOOD#QUALITY\",\"FOOD#STYLE&OPTIONS\",\"DRINKS#PRICES\",\"DRINKS#QUALITY\",\n            \"DRINKS#STYLE&OPTIONS\",\"AMBIENCE#GENERAL\",\"SERVICE#GENERAL\",\"LOCATION#GENERAL\"]\neng_polarity = [\"không có\", \"positive\",\"neutral\",\"negative\"]\ndetect_labels = ['không', 'có']\nno_polarity = len(polarity_list)\nno_tag = len(tags)\n\ndef predict(\n    model, \n    text, \n    tokenizer,\n    model_tokenize=None,\n    device='cuda', \n    processed=True,\n    printout=False):\n    \n    predicts = []\n    model.to(device)\n    model.eval()\n    model.config.use_cache = False\n    \n    if not processed:\n        text = normalize(text)\n        text = tokenize(text, model_tokenize)\n        \n    for i in range(no_tag):\n        tag = tags[i]\n        score_list = []\n        input_ids = tokenizer([text] * no_polarity, return_tensors='pt')['input_ids']\n        target_list = [\"Nhận_xét \" + tag.lower() + \" \" + polarity.lower() + \" .\" for polarity in polarity_list]\n        output_ids = tokenizer(target_list, return_tensors='pt', padding=True, truncation=True)['input_ids']\n\n        with torch.no_grad():\n            output = model(input_ids=input_ids.to(device), decoder_input_ids=output_ids.to(device))[0]\n            logits = output.softmax(dim=-1).to('cpu').numpy()\n        for m in range(no_polarity):\n            score = 1\n            for n in range(logits[m].shape[0] - 2):\n                score *= logits[m][n][output_ids[m][n+1]]\n            score_list.append(score)\n        predict = np.argmax(score_list)\n        predicts.append(predict)\n        \n    if printout:\n        result = {}\n        for i in range(no_tag):\n            if predicts[i] != 0:\n                result[eng_tags[i]] = eng_polarity[predicts[i]]\n        print(result)\n    return predicts\n    \ndef predict_df(\n    model, \n    df,\n    tokenizer=None,\n    model_tokenize=None,\n    tokenizer_name='vinai/bartpho-word-base',\n    device='cuda',\n    processed=True,\n    printout=True):\n    \n    model.eval()\n    model.to(device)\n    model.config.use_cache = False\n    if not tokenizer:\n        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)\n    count_acc = 0\n    count_detect = 0\n    f1_detect = 0\n    f1_absa = 0\n    pre_detect = 0\n    rec_detect= 0\n    pre_absa = 0\n    rec_absa = 0\n    \n    total_f1 = len(df)\n    total = len(df) * no_tag\n    \n    for i in range(total_f1):\n        text = df['text'][i]\n        labels = [df[x][i] for x in eng_tags]\n        predicts = predict(model, text, tokenizer, model_tokenize, device, processed)\n        \n        labels_detect = [i for i in range(no_tag) if labels[i] != 0]\n        predicts_detect = [i for i in range(no_tag) if predicts[i] != 0]\n        common_detect = [x for x in labels_detect if x in predicts_detect]\n        if not len(common_detect)==0:\n            precision_detect = len(common_detect)/len(predicts_detect)\n            recall_detect = len(common_detect)/len(labels_detect)\n            f1_detect += (2 * precision_detect * recall_detect / (precision_detect + recall_detect))\n            pre_detect += precision_detect\n            rec_detect += recall_detect\n        \n            labels_absa = [str(i)+'-'+str(labels[i]) for i in range(no_tag) if labels[i] != 0]\n            predicts_absa = [str(i)+'-'+str(predicts[i]) for i in range(no_tag) if predicts[i] != 0]\n            common_absa = [x for x in labels_absa if x in predicts_absa]\n            if not len(common_absa)==0:\n                precision_absa = len(common_absa)/len(predicts_absa)\n                recall_absa = len(common_absa)/len(labels_absa)\n                f1_absa += (2 * precision_absa * recall_absa / (precision_absa + recall_absa))\n                pre_absa += precision_absa\n                rec_absa += recall_absa\n        \n        for j in range(no_tag):\n            if labels[j] == predicts[j]:\n                count_acc += 1\n                count_detect += 1\n            else:\n                if labels[j] != 0 and predicts[j] !=0:\n                    count_detect += 1\n    \n    acc_detect = count_detect/total\n    pre_detect = pre_detect/total_f1\n    rec_detect = rec_detect/total_f1\n    f1_detect = f1_detect/total_f1\n    \n    acc = count_acc/total\n    pre_absa = pre_absa/total_f1\n    rec_absa = rec_absa/total_f1\n    f1_absa = f1_absa/total_f1\n    \n    if printout:\n        print(\"Detect acc: {:.4f}%\".format(acc_detect * 100))\n        print(\"Detect precision: {:.4f}%\".format(pre_detect* 100))\n        print(\"Detect recall: {:.4f}%\".format(rec_detect* 100))\n        print(\"Detect f1: {:.4f}%\".format(f1_detect * 100))\n        print()\n        print(\"Absa acc: {:.4f}%\".format(acc * 100))\n        print(\"Absa precision: {:.4f}%\".format(pre_absa * 100))\n        print(\"Absa recall: {:.4f}%\".format(rec_absa * 100))\n        print(\"Absa f1: {:.4f}%\".format(f1_absa * 100))\n    \n    return acc_detect, pre_detect, rec_detect, f1_detect, acc, pre_absa, rec_absa, f1_absa\n\ndef predict_detect(\n    model, \n    text, \n    tokenizer, \n    model_tokenize=None,\n    device='cuda', \n    processed=True,\n    printout=False):\n    \n    detect_predicts = []\n    model.to(device)\n    model.eval()\n    model.config.use_cache = False\n    \n    if not processed:\n        text = normalize(text)\n        text = tokenize(text, model_tokenize)\n        \n    for i in range(no_tag):\n        tag = tags[i]\n        detect_score_list = []\n        input_ids = tokenizer([text] * 2, return_tensors='pt')['input_ids']\n        target_list = [tag.lower() + \" \" + detect_label.lower() + \" được nhận_xét .\" for detect_label in detect_labels]\n        output_ids = tokenizer(target_list, return_tensors='pt', padding=True, truncation=True)['input_ids']\n\n        with torch.no_grad():\n            output = model(input_ids=input_ids.to(device), decoder_input_ids=output_ids.to(device))[0]\n            logits = output.softmax(dim=-1).to('cpu').numpy()\n        for m in range(2):\n            detect_score = 1\n            for n in range(logits[m].shape[0] - 2):\n                detect_score *= logits[m][n][output_ids[m][n+1]]\n            detect_score_list.append(detect_score)\n        detect_predict = np.argmax(detect_score_list)\n        detect_predicts.append(detect_predict)\n        \n    predicts = []\n    for i in range(no_tag):\n        if detect_predicts[i] == 0:\n            predicts.append(0)\n        else:\n            tag = tags[i]\n            score_list = []\n            input_ids = tokenizer([text] * (no_polarity-1), return_tensors='pt')['input_ids']\n            target_list = [\"Nhận_xét \" + tag.lower() + \" \" + polarity.lower() + \" .\" for polarity in polarity_list if polarity != \"không có\"]\n            output_ids = tokenizer(target_list, return_tensors='pt', padding=True, truncation=True)['input_ids']\n\n            with torch.no_grad():\n                output = model(input_ids=input_ids.to(device), decoder_input_ids=output_ids.to(device))[0]\n                logits = output.softmax(dim=-1).to('cpu').numpy()\n            for m in range(no_polarity-1):\n                score = 1\n                for n in range(logits[m].shape[0] - 2):\n                    score *= logits[m][n][output_ids[m][n+1]]\n                score_list.append(score)\n            predict = np.argmax(score_list) + 1\n            predicts.append(predict)\n        \n    if printout:\n        result = {}\n        for i in range(no_tag):\n            if predicts[i] != 0:\n                result[eng_tags[i]] = eng_polarity[predicts[i]]\n        print(result)\n    return predicts\n    \ndef predict_df_detect(\n    model, \n    df,\n    tokenizer=None,\n    model_tokenize=None,\n    tokenizer_name='vinai/bartpho-word-base',\n    device='cuda',\n    printout=True):\n    \n    model.eval()\n    model.to(device)\n    model.config.use_cache = False\n    if not tokenizer:\n        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)\n    count_acc = 0\n    count_detect = 0\n    f1_detect = 0\n    f1_absa = 0\n    pre_detect = 0\n    rec_detect= 0\n    pre_absa = 0\n    rec_absa = 0\n    \n    total_f1 = len(df)\n    total = len(df) * no_tag\n    \n    for i in range(total_f1):\n        text = df['text'][i]\n        labels = [df[x][i] for x in eng_tags]\n        predicts = predict(model, text, tokenizer, model_tokenize, processed, device)\n        \n        labels_detect = [i for i in range(no_tag) if labels[i] != 0]\n        predicts_detect = [i for i in range(no_tag) if predicts[i] != 0]\n        common_detect = [x for x in labels_detect if x in predicts_detect]\n        if not len(common_detect)==0:\n            precision_detect = len(common_detect)/len(predicts_detect)\n            recall_detect = len(common_detect)/len(labels_detect)\n            f1_detect += (2 * precision_detect * recall_detect / (precision_detect + recall_detect))\n            pre_detect += precision_detect\n            rec_detect += recall_detect\n        \n            labels_absa = [str(i)+'-'+str(labels[i]) for i in range(no_tag) if labels[i] != 0]\n            predicts_absa = [str(i)+'-'+str(predicts[i]) for i in range(no_tag) if predicts[i] != 0]\n            common_absa = [x for x in labels_absa if x in predicts_absa]\n            if not len(common_absa)==0:\n                precision_absa = len(common_absa)/len(predicts_absa)\n                recall_absa = len(common_absa)/len(labels_absa)\n                f1_absa += (2 * precision_absa * recall_absa / (precision_absa + recall_absa))\n                pre_absa += precision_absa\n                rec_absa += recall_absa\n        \n        for j in range(no_tag):\n            if labels[j] == predicts[j]:\n                count_acc += 1\n                count_detect += 1\n            else:\n                if labels[j] != 0 and predicts[j] !=0:\n                    count_detect += 1\n    \n    acc_detect = count_detect/total\n    pre_detect = pre_detect/total_f1\n    rec_detect = rec_detect/total_f1\n    f1_detect = f1_detect/total_f1\n    \n    acc = count_acc/total\n    pre_absa = pre_absa/total_f1\n    rec_absa = rec_absa/total_f1\n    f1_absa = f1_absa/total_f1\n    \n    if printout:\n        print(\"Detect acc: {:.4f}%\".format(acc_detect * 100))\n        print(\"Detect precision: {:.4f}%\".format(pre_detect* 100))\n        print(\"Detect recall: {:.4f}%\".format(rec_detect* 100))\n        print(\"Detect f1: {:.4f}%\".format(f1_detect * 100))\n        print()\n        print(\"Absa acc: {:.4f}%\".format(acc * 100))\n        print(\"Absa precision: {:.4f}%\".format(pre_absa * 100))\n        print(\"Absa recall: {:.4f}%\".format(rec_absa * 100))\n        print(\"Absa f1: {:.4f}%\".format(f1_absa * 100))\n    \n    return acc_detect, pre_detect, rec_detect, f1_detect, acc, pre_absa, rec_absa, f1_absa\n    ","metadata":{"_uuid":"8f2839f25d086af736a60e9eeb907d3b93b6e0e5","_cell_guid":"b1076dfc-b9ad-4769-8c92-a6c4dae69d19","trusted":true},"execution_count":null,"outputs":[]}]}