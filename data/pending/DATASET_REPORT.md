# Отчёт по новым датасетам (на утверждение)

Файлы лежат в `datasets_pending/` — **существующие датасеты проекта не тронуты**. После утверждения их можно подключить к обучению.

Метки: `0` — человек, `1` — ИИ. Формат: `code;label`, разделитель `;`, CRLF.

## JAVA

Собрано сырых примеров: 116,990 → после нормализации/дедупликации/удаления противоречий: 111,879.

| набор | строк | человек | ИИ |
|---|---|---|---|
| java_train.csv | 5996 | 2998 | 2998 |
| java_test.csv | 808 | 404 | 404 |
| java_test_ood.csv | 396 | 198 | 198 |

### Состав по источникам

**train**

| source | человек | ИИ |
|---|---|---|
| claude_handwritten | 0 | 24 |
| codemirage | 757 | 757 |
| gptsniffer | 314 | 314 |
| hvai | 629 | 629 |
| local_pairs | 228 | 204 |
| rosetta | 505 | 505 |
| semeval | 565 | 565 |

**test**

| source | человек | ИИ |
|---|---|---|
| claude_handwritten | 0 | 9 |
| codemirage | 104 | 104 |
| gptsniffer | 42 | 42 |
| hvai | 80 | 80 |
| local_pairs | 44 | 35 |
| rosetta | 61 | 61 |
| semeval | 73 | 73 |

**test_ood**

| source | человек | ИИ |
|---|---|---|
| codemirage | 128 | 128 |
| gptsniffer | 70 | 70 |

### Генераторы ИИ в train

chatgpt (552), starcoder2 (505), deepseek (235), local_ai (204), qwen (156), gemini-2.0-pro-exp (136), gemini-2.0-flash (128), deepseek-v3 (113), qwen2.5-coder (99), gpt-4o-mini (77), deepseek-r1 (72), claude-3.5-haiku (68), o3-mini (64), 01-ai/Yi-Coder-9B (34), codellama/CodeLlama-34b-Instruct-hf (30), microsoft/Phi-3.5-mini-instruct (27), meta-llama/Llama-3.3-70B-Instruct (24), Qwen/Qwen2.5-Coder-32B-Instruct (24), claude (24), meta-llama/Llama-3.1-8B-Instruct (23), microsoft/Phi-3-medium-4k-instruct (22), microsoft/Phi-3-mini-4k-instruct (21), bigcode/starcoder2-3b (21), codellama/CodeLlama-70b-Instruct-hf (21), meta-llama/Llama-3.2-3B (20), google/codegemma-2b (19), microsoft/phi-2 (19), 01-ai/Yi-Coder-1.5B-Chat (19), bigcode/starcoder2-15b (18), microsoft/Phi-3-small-8k-instruct (18), Qwen/Qwen2.5-Coder-1.5B-Instruct (18), Qwen/Qwen2.5-Coder-7B (16), deepseek-ai/deepseek-coder-6.7b-base (14), deepseek-ai/deepseek-coder-1.3b-base (14), bigcode/starcoder2-7b (13), 01-ai/Yi-Coder-9B-Chat (12), ibm-granite/granite-8b-code-instruct-4k (12), 01-ai/Yi-Coder-1.5B (12), deepseek-ai/deepseek-coder-1.3b-instruct (12), ibm-granite/granite-8b-code-base-4k (12), bigcode/starcoder (12), google/codegemma-7b (11), codellama/CodeLlama-7b-hf (10), Qwen/Qwen2.5-Coder-7B-Instruct (9), Qwen/Qwen2.5-Coder-1.5B (8), meta-llama/Llama-3.1-8B (7), meta-llama/Llama-3.2-1B (7), deepseek-ai/deepseek-coder-6.7b-instruct (6)

### Лицензии источников

| источник | лицензия | где |
|---|---|---|
| Rosetta Code / H-AIRosettaMP | MIT (данные Rosetta — GFDL) | `isThisYouLLM/H-AIRosettaMP` |
| HumanVsAICode | CC-BY-SA-4.0 | `OSS-forge/HumanVsAICode` |
| SemEval-2026 Task 13 | Apache-2.0 | `DaniilOr/SemEval-2026-Task13` |
| GPTSniffer | не указана (исследовательский) | `mahirlabibdihan/GPTSniffer` |
| Собственные данные проекта | — | `javadata.csv, java_ai_generated.csv` |
| CodeMirage (человек + 10 LLM) | CC-BY-NC-ND-4.0 (некоммерческая, без производных!) | `HanxiGuo/CodeMirage` |

### Диагностика шорткатов

- AUC простой модели на **поверхностных признаках** (длина, комментарии, отступы…): **0.666**
- AUC линейной модели на **символьных n-граммах** (test): **0.807**
- AUC той же модели на **OOD** (невиданные генераторы/источники): **0.830** — если близко к test, сигнал настоящий (стиль), а не артефакт источника

Поверхностные признаки не должны выдавать класс почти идеально (ориентир: AUC < 0.80). n-граммы — это нижняя граница «сложности» задачи; нейросеть должна заметно её превзойти.

|  | human | ai |
|---|---|---|
| len | 1362.398 | 1361.706 |
| lines | 46.215 | 43.915 |
| comment_ratio | 0.064 | 0.061 |
| blank_ratio | 0.140 | 0.126 |
| avg_line | 31.038 | 31.125 |
| max_line | 90.230 | 91.083 |
| indent_avg | 7.378 | 6.308 |
| has_doc | 0.216 | 0.093 |
| has_import | 0.536 | 0.606 |
| has_namespace | 0.002 | 0.008 |
| has_main | 0.353 | 0.406 |
| has_class | 0.756 | 0.750 |
| inline_comment | 0.260 | 0.375 |
| has_todo | 0.010 | 0.003 |
| digits_ratio | 0.012 | 0.012 |
| upper_ratio | 0.050 | 0.047 |

### Примеры (случайные)

**Человек (0):**

*источник: semeval / human*
```
import java.io.*;

import java.util.*;

public class Library {

    private static int gcd(int a, int b) {

        if(a == 0) {

            return b;

        }

        return gcd(b%a, a);

    }

    public static void main(String[] args) throws IOException {

        //BufferedReader f = new BufferedReader(new FileReader("uva.in"));

```

*источник: semeval / human*
```
import java.util.Scanner;

public class code{

    public static void main(String args[]){

        Scanner s = new Scanner(System.in);

        int t = s.nextInt();

        while(t-->0){

           long n = s.nextLong();

           long k = s.nextLong();

           boolean bool = false;

           if(n%2==0 && k%2==0 || n%2!=0 && k%2!=0){

               bool = true;

```

**ИИ (1):**

*источник: gptsniffer / chatgpt*
```
public class HexFormatException extends Exception {
    public HexFormatException(String message) {
        super(message);
    }
}

public class HexConverter {
    public static int hex2Dec(String hexString) throws HexFormatException {
        int decimalValue = 0;
        for (int i = 0; i < hexString.length(); i++) {
            char hexChar = hexString.charAt(i);
            if (!(hexChar >= '0' && hexChar <= '9') &&
                !(hexChar >= 'A' && hexChar <= 'F') &&
                !(hexChar >= 'a' && hexChar <= 'f')) {
                throw new HexFormatException("Invalid hex string: " + hexString);
            }
            decimalValue = decimalValue * 16 + hexToDecimal(hexChar);
        }
        return decimalValue;
    }

    public static int hexToDecimal(char ch) {
```

*источник: codemirage / gemini-2.0-pro-exp*
```
import com.github.scribejava.apis.GoogleApi20;
import com.github.scribejava.core.builder.api.DefaultApi20;
import edu.harvard.iq.dataverse.authorization.AuthenticatedUserDisplayInfo;
import java.io.StringReader;
import java.util.UUID;
import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import static edu.harvard.iq.dataverse.util.BundleUtil.getStringFromBundle;

public class GoogleOAuth2AP extends AbstractOAuth2AuthenticationProvider {

    private final String clientId;
    private final String clientSecret;
    private final String scope = "profile email";
    private final String baseUserEndpoint = "https://www.googleapis.com/oauth2/v3/userinfo";
    private static final String id = "google";
    private static final String title = "Google";

    public GoogleOAuth2AP(String clientId, String clientSecret) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
```

## KOTLIN

Собрано сырых примеров: 92,420 → после нормализации/дедупликации/удаления противоречий: 86,631.

| набор | строк | человек | ИИ |
|---|---|---|---|
| kotlin_train.csv | 4998 | 2499 | 2499 |
| kotlin_test.csv | 700 | 350 | 350 |
| kotlin_test_ood.csv | 498 | 249 | 249 |

### Состав по источникам

**train**

| source | человек | ИИ |
|---|---|---|
| kstack | 1719 | 0 |
| rlvr | 0 | 1719 |
| rosetta | 780 | 780 |

**test**

| source | человек | ИИ |
|---|---|---|
| kstack | 222 | 0 |
| rlvr | 0 | 222 |
| rosetta | 128 | 128 |

**test_ood**

| source | человек | ИИ |
|---|---|---|
| kexercises | 0 | 249 |
| kstack | 249 | 0 |

### Генераторы ИИ в train

llm-modern (1719), starcoder2 (780)

### Лицензии источников

| источник | лицензия | где |
|---|---|---|
| Rosetta Code / H-AIRosettaMP | MIT (данные Rosetta — GFDL) | `isThisYouLLM/H-AIRosettaMP` |
| KStack-clean (человек) | Apache-2.0/MIT/Unlicense/CC0/ISC/BSD — берутся только они | `JetBrains/KStack-clean` |
| KExercises (ИИ, GPT-3.5) | CC-BY-NC-SA-4.0 (некоммерческая) | `JetBrains/KExercises` |
| rlvr-code-data-Kotlin (ИИ) | не указана | `saurabh5/rlvr-code-data-Kotlin` |

### Диагностика шорткатов

- AUC простой модели на **поверхностных признаках** (длина, комментарии, отступы…): **0.784**
- AUC линейной модели на **символьных n-граммах** (test): **0.927**
- AUC той же модели на **OOD** (невиданные генераторы/источники): **0.931** — если близко к test, сигнал настоящий (стиль), а не артефакт источника

Поверхностные признаки не должны выдавать класс почти идеально (ориентир: AUC < 0.80). n-граммы — это нижняя граница «сложности» задачи; нейросеть должна заметно её превзойти.

|  | human | ai |
|---|---|---|
| len | 716.418 | 722.289 |
| lines | 23.117 | 24.060 |
| comment_ratio | 0.039 | 0.060 |
| blank_ratio | 0.091 | 0.049 |
| avg_line | 31.965 | 31.348 |
| max_line | 80.748 | 80.603 |
| indent_avg | 5.307 | 5.177 |
| has_doc | 0.060 | 0.018 |
| has_import | 0.118 | 0.177 |
| has_namespace | 0.000 | 0.001 |
| has_main | 0.413 | 0.237 |
| has_class | 0.093 | 0.088 |
| inline_comment | 0.217 | 0.328 |
| has_todo | 0.003 | 0.001 |
| digits_ratio | 0.021 | 0.017 |
| upper_ratio | 0.046 | 0.043 |

### Примеры (случайные)

**Человек (0):**

*источник: kstack / human*
```
fun Char.isOpeningBracket() = listOf('(', '[', '{', '<').contains(this)

infix fun Char.doesNotClose(openingChar: Char) = !(this closes openingChar)
infix fun Char.closes(openingBracket: Char) = openingBracket.findClosingBracket() == this

fun Char.findClosingBracket() = when (this) {
    '(' -> ')'
    '[' -> ']'
    '{' -> '}'
    '<' -> '>'
    else -> throw IllegalArgumentException("Invalid opening char: $this")
}

val Char.syntaxErrorScore
    get() = when (this) {
        ')' -> 3
        ']' -> 57
        '}' -> 1197
        '>' -> 25137
        else -> throw IllegalArgumentException("Invalid closing char: $this")
    }
```

*источник: kstack / human*
```
fun encodeString(stringToEncode: String, dictionary: Map<String, String>): String {
    val stringBuilder = StringBuilder()
    stringToEncode.forEach { stringBuilder.append(dictionary[it.toString()]) }

    return stringBuilder.toString()
}
```

**ИИ (1):**

*источник: rlvr / llm-modern*
```
fun findSubset(inputList: List<Int>, target: Int): List<Int> {
    val dp = mutableMapOf<Int, List<Int>>()
    dp[0] = listOf()
    for (num in inputList) {
        val keys = dp.keys.toList()
        for (s in keys) {
            val newSum = s + num
            if (!dp.containsKey(newSum)) {
                val newSubset = dp[s]!! + num
                if (newSum == target) {
                    return newSubset
                }
                dp[newSum] = newSubset
            }
        }
    }
    return listOf()
}
```

*источник: rlvr / llm-modern*
```
fun encryptData(data: String): String {
    val encrypted = StringBuilder()
    for (char in data) {
        if (char.isLetter()) {
            if (char.isUpperCase()) {
                encrypted.append(((char.code - 'A'.code + 3) % 26 + 'A'.code).toChar())
            } else {
                encrypted.append(((char.code - 'a'.code + 3) % 26 + 'a'.code).toChar())
            }
        } else {
            encrypted.append(char)
        }
    }
    return encrypted.toString()
}
```

## CSHARP

Собрано сырых примеров: 31,842 → после нормализации/дедупликации/удаления противоречий: 27,253.

| набор | строк | человек | ИИ |
|---|---|---|---|
| csharp_train.csv | 5002 | 2501 | 2501 |
| csharp_test.csv | 702 | 351 | 351 |
| csharp_test_ood.csv | 194 | 97 | 97 |

### Состав по источникам

**train**

| source | человек | ИИ |
|---|---|---|
| codemirage | 452 | 1854 |
| lcc | 1402 | 0 |
| rosetta | 647 | 647 |

**test**

| source | человек | ИИ |
|---|---|---|
| codemirage | 63 | 256 |
| lcc | 193 | 0 |
| rosetta | 95 | 95 |

**test_ood**

| source | человек | ИИ |
|---|---|---|
| codemirage | 97 | 97 |

### Генераторы ИИ в train

starcoder2 (647), o3-mini (427), gpt-4o-mini (301), claude-3.5-haiku (274), qwen2.5-coder (243), deepseek-r1 (236), deepseek-v3 (160), gemini-2.0-flash (135), gemini-2.0-pro-exp (78)

### Лицензии источников

| источник | лицензия | где |
|---|---|---|
| Rosetta Code / H-AIRosettaMP | MIT (данные Rosetta — GFDL) | `isThisYouLLM/H-AIRosettaMP` |
| LCC_csharp (человек) | не указана (GitHub, The Stack) | `microsoft/LCC_csharp` |
| CodeMirage (человек + 10 LLM) | CC-BY-NC-ND-4.0 (некоммерческая, без производных!) | `HanxiGuo/CodeMirage` |

### Диагностика шорткатов

- AUC простой модели на **поверхностных признаках** (длина, комментарии, отступы…): **0.791**
- AUC линейной модели на **символьных n-граммах** (test): **0.921**
- AUC той же модели на **OOD** (невиданные генераторы/источники): **0.820** — если близко к test, сигнал настоящий (стиль), а не артефакт источника

Поверхностные признаки не должны выдавать класс почти идеально (ориентир: AUC < 0.80). n-граммы — это нижняя граница «сложности» задачи; нейросеть должна заметно её превзойти.

|  | human | ai |
|---|---|---|
| len | 2075.082 | 2080.424 |
| lines | 61.146 | 68.805 |
| comment_ratio | 0.146 | 0.066 |
| blank_ratio | 0.121 | 0.125 |
| avg_line | 33.596 | 29.408 |
| max_line | 112.022 | 101.481 |
| indent_avg | 7.859 | 7.821 |
| has_doc | 0.022 | 0.002 |
| has_import | 0.934 | 0.950 |
| has_namespace | 0.806 | 0.600 |
| has_main | 0.002 | 0.004 |
| has_class | 0.934 | 0.945 |
| inline_comment | 0.633 | 0.500 |
| has_todo | 0.021 | 0.003 |
| digits_ratio | 0.012 | 0.010 |
| upper_ratio | 0.064 | 0.057 |

### Примеры (случайные)

**Человек (0):**

*источник: lcc / human*
```
using System;
using System.IO;
using System.Threading;

using MimeKit.IO;

namespace MimeKit {
    /// <summary>
    /// A MIME part containing a <see cref="MimeKit.MimeMessage"/> as its content.
    /// </summary>
    /// <remarks>
    /// Represents MIME entities such as those with a Content-Type of message/rfc822 or message/news.
    /// </remarks>
    public class MessagePart : MimeEntity
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="MimeKit.MessagePart"/> class.
        /// </summary>
        /// <remarks>
        /// This constructor is used by <see cref="MimeKit.MimeParser"/>.
        /// </remarks>
        /// <param name="args">Information used by the constructor.</param>
```

*источник: lcc / human*
```
using UnityEditor;
using UnityEngine;
using System.Collections.Generic;

[CanEditMultipleObjects]
[CustomEditor(typeof(tk2dTextMesh))]
class tk2dTextMeshEditor : Editor
{
    tk2dGenericIndexItem[] allFonts = null; // all generators
    string[] allFontNames = null;
    Vector2 gradientScroll;

    // Word wrap on text area - almost impossible to use otherwise
    GUIStyle _textAreaStyle = null;
    GUIStyle textAreaStyle
    {
        get {
            if (_textAreaStyle == null)
            {
                _textAreaStyle = new GUIStyle(EditorStyles.textField);
                _textAreaStyle.wordWrap = true;
            }
```

**ИИ (1):**

*источник: codemirage / claude-3.5-haiku*
```
using System;
using System.Net;
using System.Net.Mail;
using System.Configuration;

namespace FashionApp.Utilities
{
    public class EmailSettings
    {
        // Email configuration properties
        public string Link { get; set; }
        public string MailFromAddress { get; private set; }
        public string ServerName { get; private set; }
        public bool UseSsl { get; private set; }
        public int ServerPort { get; private set; }
        private string Username { get; set; }
        private string Password { get; set; }

        // Constructor to initialize email settings
        public EmailSettings()
        {
            // Default Gmail SMTP Configuration
```

*источник: codemirage / gemini-2.0-flash*
```
using System;
using System.Collections.Generic;
using System.Linq;
using hw.DebugFormatter;
using hw.Scanner;
using hw.UnitTest;
using Reni;

namespace AutoCompleteTest
{
    [UnitTest]
    public sealed class AutoComplete
    {
        [UnitTest]
        public void DeclarationOptions()
        {
            const string text = @"
type Array16: Array(16, UInt1)

define array16_0: Array16()
define array16_1: Array16(1)

```
