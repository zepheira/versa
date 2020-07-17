# -*- coding: utf-8 -*-
# test_serial_csv.py
'''
Test CSV serializer

pytest -s test/py/test_serial_csv.py
'''

import logging
import functools
from collections import OrderedDict 

# Requires pytest-mock
import pytest
from amara3 import iri

from versa import I
from versa.driver.memory import newmodel
from versa.serial.csv import *
# from versa.util import jsondump, jsonload

# Sample use pattern
def csvmock(_):
    od = OrderedDict([('Wikidata', 'Q15761337'), ('©', '2016'), ('WD link', 'link -->'), ('Journal title', 'Časopis pro Moderní Filologii'), ('Alternative title', 'Journal for Modern Philology'), ('Journal URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/'), ('Journal ISSN (print version)', '0008-7386'), ('Journal EISSN (online version)', '2336-6591'), ('Publisher', 'Univerzita Karlova v Praze, Filolozofická faku'), ('Publisher Q ', 'Q52664773'), ('Disambiguation publisher', ''), ('Subjects', 'Language and Literature: Philology. Linguistics'), ('Keywords', 'philology, linguistics'), ('Society or institution', 'Univerzita Karlova v Praze, Filozofická fakulta'), ('Platform, host or aggregator', 'Digitool'), ('Country of publisher', 'Czech Republic'), ('Country of Publisher Q item', 'Q213'), ('Journal article processing charges (APCs)', 'No'), ('Article Processing Charge information URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('APC amount', ''), ('Currency', ''), ('Journal article submission fee', ''), ('Submission fee URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Submission fee amount', ''), ('Submission fee currency', ''), ('Number of articles publish in the last calendar year', ''), ('Number of articles information URL', ''), ('Journal waiver policy (for developing country authors etc)', ''), ('Waiver policy information URL', ''), ('Digital archiving policy or program(s)', ''), ('Archiving: national library', ''), ('Archiving: other', ''), ('Archiving infomation URL', ''), ('Journal full-text crawl permission', 'Yes'), ('Permanent article identifiers', ''), ('Journal provides download statistics', ''), ('Download statistics information URL', ''), ('First calendar year journal provided online Open Access content', '2015'), ('Full text formats', 'PDF'), ('Full text language', 'Czech, English'), ('URL for the Editorial Board page', 'http://casopispromodernifilologii.ff.cuni.cz/en/editorial-board/'), ('Review process', 'Double blind peer review'), ('Review process information URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/review-process/'), ("URL for journal's aims & scope", 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ("URL for journal's instructions for authors", 'http://casopispromodernifilologii.ff.cuni.cz/en/guidelines/'), ('Journal plagiarism screening policy', ''), ('Plagiarism information URL', ''), ('Average number of weeks between submission and publication', '22'), ("URL for journal's Open Access statement", 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Machine-readable CC licensing information embedded or displayed in articles', ''), ('URL to an example page with embedded licensing information', ''), ('Journal license', 'CC BY-NC-ND'), ('License attributes', ''), ('Licence item', 'Q6937225'), ('URL for license terms', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Does this journal allow unrestricted reuse in compliance with BOAI?', 'Yes'), ('Deposit policy directory', ''), ('Author holds copyright without restrictions', 'FALSE'), ('Copyright information URL', ''), ('Author holds publishing rights without restrictions', 'FALSE'), ('Publishing rights information URL', ''), ('DOAJ Seal', 'No'), ('Tick: Accepted after March 2014', 'Yes'), ('Added on Date', '2016-01-23T09:34:47Z'), ('', ''), ('Wikidata_match', 'Q15761337'), ('WD_link', 'link -->'), ('Journal_title', 'Časopis pro Moderní Filologii'), ('Alternative_title', 'Journal for Modern Philology'), ('Journal_URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/'), ('Journal_ISSN__print_version_', '0008-7386'), ('Journal_EISSN__online_version_', '2336-6591'), ('Publisher_Q_', 'Q52664773'), ('Disambiguation_publisher', ''), ('Society_or_institution', 'Univerzita Karlova v Praze, Filozofická fakulta'), ('Platform__host_or_aggregator', 'Digitool'), ('Country_of_publisher', 'Czech Republic'), ('Country_of_Publisher_Q_item', 'Q213'), ('Journal_article_processing_charges__APCs_', 'No'), ('Article_Processing_Charge_information_URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('APC_amount', ''), ('Journal_article_submission_fee', ''), ('Submission_fee_URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Submission_fee_amount', ''), ('Submission_fee_currency', ''), ('Number_of_articles_publish_in_the_last_calendar_year', ''), ('Number_of_articles_information_URL', ''), ('Journal_waiver_policy__for_developing_country_authors_etc_', ''), ('Waiver_policy_information_URL', ''), ('Digital_archiving_policy_or_program_s_', ''), ('Archiving__national_library', ''), ('Archiving__other', ''), ('Archiving_infomation_URL', ''), ('Journal_full-text_crawl_permission', 'Yes'), ('Permanent_article_identifiers', ''), ('Journal_provides_download_statistics', ''), ('Download_statistics_information_URL', ''), ('First_calendar_year_journal_provided_online_Open_Access_content', '2015'), ('Full_text_formats', 'PDF'), ('Full_text_language', 'Czech, English'), ('URL_for_the_Editorial_Board_page', 'http://casopispromodernifilologii.ff.cuni.cz/en/editorial-board/'), ('Review_process', 'Double blind peer review'), ('Review_process_information_URL', 'http://casopispromodernifilologii.ff.cuni.cz/en/review-process/'), ('URL_for_journal_s_aims___scope', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('URL_for_journal_s_instructions_for_authors', 'http://casopispromodernifilologii.ff.cuni.cz/en/guidelines/'), ('Journal_plagiarism_screening_policy', ''), ('Plagiarism_information_URL', ''), ('Average_number_of_weeks_between_submission_and_publication', '22'), ('URL_for_journal_s_Open_Access_statement', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Machine-readable_CC_licensing_information_embedded_or_displayed_in_articles', ''), ('URL_to_an_example_page_with_embedded_licensing_information', ''), ('Journal_license', 'CC BY-NC-ND'), ('License_attributes', ''), ('Licence_item', 'Q6937225'), ('URL_for_license_terms', 'http://casopispromodernifilologii.ff.cuni.cz/en/about-journal-4/'), ('Does_this_journal_allow_unrestricted_reuse_in_compliance_with_BOAI_', 'Yes'), ('Deposit_policy_directory', ''), ('Author_holds_copyright_without_restrictions', 'FALSE'), ('Copyright_information_URL', ''), ('Author_holds_publishing_rights_without_restrictions', 'FALSE'), ('Publishing_rights_information_URL', ''), ('DOAJ_Seal', 'No'), ('Tick__Accepted_after_March_2014', 'Yes'), ('Added_on_Date', '2016-01-23T09:34:47Z')])
    return [od]


def test_csv_usecase1():
    m = newmodel()
    tmpl = '# http://example.org#{Wikidata}\n\n * <http://example.org/voc/copyright>: {%C2%A9}'
    # use -s option to see the nosy print
    m = next(parse_iter(object(), tmpl, csv_fact=csvmock, nosy=print))
    
    assert len(m) == 1, repr(m)
    assert ('http://example.org#Q15761337', 'http://example.org/voc/copyright', '2016', {}) == next(m.match())
